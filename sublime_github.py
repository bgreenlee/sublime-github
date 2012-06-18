import os
import os.path
import sublime
import sublime_plugin
import webbrowser
import plistlib
from github import GitHubApi
import logging as logger
try:
    import xml.parsers.expat as expat
except ImportError:
    expat = None

logger.basicConfig(format='[sublime-github] %(levelname)s: %(message)s')


class BaseGitHubCommand(sublime_plugin.TextCommand):
    """
    Base class for all GitHub commands. Handles getting an auth token.
    """
    MSG_USERNAME = "GitHub username:"
    MSG_PASSWORD = "GitHub password:"
    MSG_TOKEN_SUCCESS = "Your access token has been saved. We'll now resume your command."
    ERR_NO_USER_TOKEN = "Your GitHub Gist access token needs to be configured.\n\n"\
        "Click OK and then enter your GitHub username and password below (neither will "\
        "be stored; they are only used to generate an access token)."
    ERR_UNAUTHORIZED = "Your Github username or password appears to be incorrect. "\
        "Please try again."
    ERR_UNAUTHORIZED_TOKEN = "Your Github token appears to be incorrect. Please re-enter your "\
        "username and password to generate a new token."

    def run(self, edit):
        self.settings = sublime.load_settings("GitHub.sublime-settings")
        self.github_user = None
        self.github_token = self.settings.get('github_token')
        self.debug = self.settings.get('debug')

    def get_token(self):
        sublime.error_message(self.ERR_NO_USER_TOKEN)
        self.get_username()

    def get_username(self):
        self.view.window().show_input_panel(self.MSG_USERNAME, self.github_user or "", self.on_done_username, None, None)

    def get_password(self):
        self.view.window().show_input_panel(self.MSG_PASSWORD, "", self.on_done_password, None, None)

    def on_done_username(self, value):
        "Callback for the username show_input_panel."
        self.github_user = value
        # need to do this or the input panel doesn't show
        sublime.set_timeout(self.get_password, 50)

    def on_done_password(self, value):
        "Callback for the password show_input_panel"
        try:
            self.github_token = GitHubApi(debug=self.debug).get_token(self.github_user, value)
            self.settings.set("github_token", self.github_token)
            sublime.save_settings("GitHub.sublime-settings")
            if self.callback:
                sublime.error_message(self.MSG_TOKEN_SUCCESS)
                callback = self.callback
                self.callback = None
                sublime.set_timeout(callback, 50)
        except GitHubApi.UnauthorizedException:
            sublime.error_message(self.ERR_UNAUTHORIZED)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException, e:
            sublime.error_message(e.message)


class OpenGistCommand(BaseGitHubCommand):
    """
    Open a gist.
    Defaults to all gists and copying it to the clipboard
    """
    MSG_SUCCESS = "Contents of '%s' copied to the clipboard."
    starred = False
    open_in_editor = False
    syntax_file_map = None
    copy_gist_id = False

    def run(self, edit):
        super(OpenGistCommand, self).run(edit)
        if self.github_token:
            self.get_gists()
        else:
            self.callback = self.get_gists
            self.get_token()

    def get_gists(self):
        self.gistapi = GitHubApi(self.github_token, debug=self.debug)
        try:
            self.gists = self.gistapi.list_gists(starred=self.starred)
            format = self.settings.get("gist_list_format")
            packed_gists = []
            for idx, gist in enumerate(self.gists):
                attribs = {"index": idx + 1,
                           "filename": gist["files"].keys()[0],
                           "description": gist["description"] or ''}
                if isinstance(format, basestring):
                    item = format % attribs
                else:
                    item = [(format_str % attribs) for format_str in format]
                packed_gists.append(item)

            args = [packed_gists, self.on_done]
            if self.settings.get("gist_list_monospace"):
                args.append(sublime.MONOSPACE_FONT)
            self.view.window().show_quick_panel(*args)
        except GitHubApi.UnauthorizedException:
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException, e:
            sublime.error_message(e.message)

    def on_done(self, idx):
        if idx == -1:
            return
        gist = self.gists[idx]
        filename = gist["files"].keys()[0]
        filedata = gist["files"][filename]
        content = self.gistapi.get(filedata["raw_url"])
        if self.open_in_editor:
            new_view = self.view.window().new_file()
            if expat:  # not present in Linux
                # set syntax file
                if not self.syntax_file_map:
                    self.syntax_file_map = self._generate_syntax_file_map()
                try:
                    extension = os.path.splitext(filename)[1][1:].lower()
                    syntax_file = self.syntax_file_map[extension]
                    new_view.set_syntax_file(syntax_file)
                except KeyError:
                    logger.warn("no mapping for '%s'" % extension)
                    pass
            # insert the gist
            edit = new_view.begin_edit('gist')
            new_view.insert(edit, 0, content)
            new_view.end_edit(edit)
            new_view.set_name(filename)
            new_view.settings().set('gist', gist)
        elif self.copy_gist_id:
            sublime.set_clipboard(gist["html_url"])
        else:
            sublime.set_clipboard(content)
            sublime.status_message(self.MSG_SUCCESS % filename)

    @staticmethod
    def _generate_syntax_file_map():
        syntax_file_map = {}
        packages_path = sublime.packages_path()
        packages = [f for f in os.listdir(packages_path) if os.path.isdir(os.path.join(packages_path, f))]
        for package in packages:
            package_dir = os.path.join(packages_path, package)
            syntax_files = [os.path.join(package_dir, f) for f in os.listdir(package_dir) if f.endswith(".tmLanguage")]
            for syntax_file in syntax_files:
                try:
                    plist = plistlib.readPlist(syntax_file)
                    if plist:
                        for file_type in plist['fileTypes']:
                            syntax_file_map[file_type.lower()] = syntax_file
                except expat.ExpatError:  # can't parse
                    logger.warn("could not parse '%s'" % syntax_file)
                except KeyError:  # no file types
                    pass

        return syntax_file_map


class OpenStarredGistCommand(OpenGistCommand):
    """
    Browse starred gists
    """
    starred = True


class OpenGistInEditorCommand(OpenGistCommand):
    """
    Open a gist in a new editor.
    """
    open_in_editor = True

class OpenGistUrlCommand(OpenGistCommand):
    """
    Open a gist url in a new editor.
    """
    copy_gist_id = True

class OpenStarredGistInEditorCommand(OpenGistCommand):
    """
    Open a starred gist in a new editor.
    """
    starred = True
    open_in_editor = True


class OpenGistInBrowserCommand(OpenGistCommand):
    """
    Open a gist in a browser
    """
    def on_done(self, idx):
        if idx == -1:
            return
        gist = self.gists[idx]
        webbrowser.open(gist["html_url"])


class OpenStarredGistInBrowserCommand(OpenGistInBrowserCommand):
    """
    Open a gist in a browser
    """
    starred = True


class GistFromSelectionCommand(BaseGitHubCommand):
    """
    Base class for creating a Github Gist from the current selection.
    """
    MSG_DESCRIPTION = "Gist description:"
    MSG_FILENAME = "Gist filename:"
    MSG_SUCCESS = "Gist created and url copied to the clipboard."

    def run(self, edit):
        self.description = None
        self.filename = None
        super(GistFromSelectionCommand, self).run(edit)
        if self.github_token:
            self.get_description()
        else:
            self.callback = self.get_description
            self.get_token()

    def get_description(self):
        self.view.window().show_input_panel(self.MSG_DESCRIPTION, "", self.on_done_description, None, None)

    def get_filename(self):
        # use the current filename as the default
        current_filename = self.view.file_name() or "snippet.txt"
        filename = os.path.basename(current_filename)
        self.view.window().show_input_panel(self.MSG_FILENAME, filename, self.on_done_filename, None, None)

    def on_done_description(self, value):
        "Callback for description show_input_panel."
        self.description = value
        # need to do this or the input panel doesn't show
        sublime.set_timeout(self.get_filename, 50)

    def on_done_filename(self, value):
        self.filename = value
        # get selected text, or the whole file if nothing selected
        if all([region.empty() for region in self.view.sel()]):
            text = self.view.substr(sublime.Region(0, self.view.size()))
        else:
            text = "\n".join([self.view.substr(region) for region in self.view.sel()])

        gistapi = GitHubApi(self.github_token, debug=self.debug)
        try:
            gist_url = gistapi.create_gist(description=self.description,
                                           filename=self.filename,
                                           content=text,
                                           public=self.public)
            sublime.set_clipboard(gist_url)
            sublime.status_message(self.MSG_SUCCESS)
        except GitHubApi.UnauthorizedException:
            # clear out the bad token so we can reset it
            self.settings.set("github_token", "")
            sublime.save_settings("GitHub.sublime-settings")
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException, e:
            sublime.error_message(e.message)


class PrivateGistFromSelectionCommand(GistFromSelectionCommand):
    """
    Command to create a private Github gist from the current selection.
    """
    public = False


class PublicGistFromSelectionCommand(GistFromSelectionCommand):
    """
    Command to create a public Github gist from the current selection.
    """
    public = True


class UpdateGistCommand(BaseGitHubCommand):
    MSG_SUCCESS = "Gist updated and url copied to the clipboard."

    def run(self, edit):
        super(UpdateGistCommand, self).run(edit)
        self.gist = self.view.settings().get('gist')
        if not self.gist:
            sublime.error_message("Can't update: this doesn't appear to be a valid gist.")
            return
        if self.github_token:
            self.update()
        else:
            self.callback = self.update
            self.get_token()

    def update(self):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        gistapi = GitHubApi(self.github_token, debug=self.debug)
        try:
            gist_url = gistapi.update_gist(self.gist, text)
            sublime.set_clipboard(gist_url)
            sublime.status_message(self.MSG_SUCCESS)
        except GitHubApi.UnauthorizedException:
            # clear out the bad token so we can reset it
            self.settings.set("github_token", "")
            sublime.save_settings("GitHub.sublime-settings")
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException, e:
            sublime.error_message(e.message)
