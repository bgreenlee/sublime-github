"""
SublimeGitHub commands
"""
import os
import os.path
import sys
import re
import logging as logger
import plistlib
import sublime
import sublime_plugin
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from github import GitHubApi
try:
    import xml.parsers.expat as expat
except ImportError:
    expat = None

VERSION = "1.4.0"

try:
    sys.path.append(os.path.join(sublime.packages_path(), 'Git'))
    import git
    sys.path.remove(os.path.join(sublime.packages_path(), 'Git'))
except ImportError:
    git = None


logger.basicConfig(format='[sublime-github] %(levelname)s: %(message)s')


class BaseGitHubCommand(sublime_plugin.TextCommand):
    """
    Base class for all GitHub commands. Handles getting an auth token.
    """
    MSG_USERNAME = "GitHub username:"
    MSG_PASSWORD = "GitHub password:"
    MSG_ONE_TIME_PASSWORD = "One-time password (for 2FA):"
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
        self.github_password = None
        self.github_one_time_password = None
        self.accounts = self.settings.get("accounts")
        self.active_account = self.settings.get("active_account")
        if not self.active_account:
            self.active_account = list(self.accounts.keys())[0]
        self.github_token = self.accounts[self.active_account]["github_token"]
        if not self.github_token:
            self.github_token = self.settings.get("github_token")
            if self.github_token:
                # migrate to new structure
                self.settings.set("accounts", {"GitHub": {"base_uri": "https://api.github.com", "github_token": self.github_token}})
                self.settings.set("active_account", "GitHub")
                self.active_account = self.settings.get("active_account")
                self.settings.erase("github_token")
                sublime.save_settings("GitHub.sublime-settings")
        self.base_uri = self.accounts[self.active_account]["base_uri"]
        self.debug = self.settings.get('debug')

        self.proxies = {'https': self.accounts[self.active_account].get("https_proxy", None)}
        self.force_curl = self.accounts[self.active_account].get("force_curl", False)
        self.gistapi = GitHubApi(self.base_uri, self.github_token, debug=self.debug,
                                 proxies=self.proxies, force_curl=self.force_curl)

    def get_token(self):
        sublime.error_message(self.ERR_NO_USER_TOKEN)
        self.get_username()

    def get_username(self):
        self.view.window().show_input_panel(self.MSG_USERNAME, self.github_user or "", self.on_done_username, None, None)

    def get_password(self):
        self.view.window().show_input_panel(self.MSG_PASSWORD, "", self.on_done_password, None, None)

    def get_one_time_password(self):
        self.view.window().show_input_panel(self.MSG_ONE_TIME_PASSWORD, "", self.on_done_one_time_password, None, None)

    def on_done_username(self, value):
        "Callback for the username show_input_panel."
        self.github_user = value
        # need to do this or the input panel doesn't show
        sublime.set_timeout(self.get_password, 50)

    def on_done_one_time_password(self, value):
        "Callback for the one-time password show_input_panel"
        self.github_one_time_password = value
        self.on_done_password(self.github_password)

    def on_done_password(self, value):
        "Callback for the password show_input_panel"
        self.github_password = value
        try:
            api = GitHubApi(self.base_uri, debug=self.debug)
            self.github_token = api.get_token(self.github_user,
                                              self.github_password,
                                              self.github_one_time_password)
            self.github_password = self.github_one_time_password = None  # don't keep these around
            self.accounts[self.active_account]["github_token"] = self.github_token
            self.settings.set("accounts", self.accounts)
            sublime.save_settings("GitHub.sublime-settings")
            self.gistapi = GitHubApi(self.base_uri, self.github_token, debug=self.debug)
            try:
                if self.callback:
                    sublime.error_message(self.MSG_TOKEN_SUCCESS)
                    callback = self.callback
                    self.callback = None
                    sublime.set_timeout(callback, 50)
            except AttributeError:
                pass
        except GitHubApi.OTPNeededException:
            sublime.set_timeout(self.get_one_time_password, 50)
        except GitHubApi.UnauthorizedException:
            sublime.error_message(self.ERR_UNAUTHORIZED)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException as e:
            sublime.error_message(e.message)


class InsertTextCommand(sublime_plugin.TextCommand):
    """
    Internal command to insert text into a view.
    """
    def run(self, edit, **args):
        self.view.insert(edit, 0, args['text'])


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
        try:
            self.gists = self.gistapi.list_gists(starred=self.starred)
            sort_by, sort_reversed = self.settings.get("gist_list_sort_by", [None, False])
            if sort_by:
                self.gists = sorted(self.gists, key=lambda x: (x.get(sort_by) or "").lower(), reverse=sort_reversed)
            gist_list_format = self.settings.get("gist_list_format")
            packed_gists = []
            for idx, gist in enumerate(self.gists):
                attribs = {"index": idx + 1,
                           "filename": list(gist["files"].keys())[0],
                           "description": gist["description"] or ''}
                if isinstance(gist_list_format, list):
                    item = [(format_str % attribs) for format_str in gist_list_format]
                else:
                    item = gist_list_format % attribs
                packed_gists.append(item)

            args = [packed_gists, self.on_done]
            if self.settings.get("gist_list_monospace"):
                args.append(sublime.MONOSPACE_FONT)
            self.view.window().show_quick_panel(*args)
        except GitHubApi.UnauthorizedException:
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException as e:
            sublime.error_message(e.message)

    def on_done(self, idx):
        if idx == -1:
            return
        gist = self.gists[idx]
        filename = list(gist["files"].keys())[0]
        content = self.gistapi.get_gist(gist)
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
                    logger.warn("no mapping for '%s'", extension)

            # insert the gist
            new_view.run_command("insert_text", {'text': content})
            new_view.set_name(filename)
            new_view.settings().set('gist', gist)
        elif self.copy_gist_id:
            sublime.set_clipboard(gist["html_url"])
        else:
            sublime.set_clipboard(content)
            sublime.status_message(self.MSG_SUCCESS % filename)

    @staticmethod
    def _generate_syntax_file_map():
        """
        Generate a map of all file types to their syntax files.
        """
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
                    logger.warn("could not parse '%s'", syntax_file)
                except KeyError:  # no file types
                    pass

        # load ST3 syntax files
        if hasattr(sublime, "find_resources"):
            syntax_files = sublime.find_resources("*.tmLanguage")
            for syntax_file in syntax_files:
                try:
                    plist = plistlib.readPlistFromBytes(bytearray(sublime.load_resource(syntax_file), "utf-8"))
                    if plist:
                        for file_type in plist['fileTypes']:
                            syntax_file_map[file_type.lower()] = syntax_file
                except expat.ExpatError:  # can't parse
                    logger.warn("could not parse '%s'", syntax_file)
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
        sublime.active_window().run_command('open_url', {'url': gist['html_url']})


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

        try:
            gist = self.gistapi.create_gist(description=self.description,
                                            filename=self.filename,
                                            content=text,
                                            public=self.public)
            self.view.settings().set('gist', gist)
            sublime.set_clipboard(gist["html_url"])
            sublime.status_message(self.MSG_SUCCESS)
        except GitHubApi.UnauthorizedException:
            # clear out the bad token so we can reset it
            self.settings.set("github_token", "")
            sublime.save_settings("GitHub.sublime-settings")
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException as e:
            sublime.error_message(e.message)
        except GitHubApi.ConnectionException as e:
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
        try:
            updated_gist = self.gistapi.update_gist(self.gist, text)
            sublime.set_clipboard(updated_gist["html_url"])
            sublime.status_message(self.MSG_SUCCESS)
        except GitHubApi.UnauthorizedException:
            # clear out the bad token so we can reset it
            self.settings.set("github_token", "")
            sublime.save_settings("GitHub.sublime-settings")
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
            sublime.set_timeout(self.get_username, 50)
        except GitHubApi.UnknownException as e:
            sublime.error_message(e.message)


class SwitchAccountsCommand(BaseGitHubCommand):
    def run(self, edit):
        super(SwitchAccountsCommand, self).run(edit)
        accounts = list(self.accounts.keys())
        self.view.window().show_quick_panel(accounts, self.account_selected)

    def account_selected(self, index):
        if index == -1:
            return  # canceled
        else:
            self.active_account = list(self.accounts.keys())[index]
            self.settings.set("active_account", self.active_account)
            sublime.save_settings("GitHub.sublime-settings")
            self.base_uri = self.accounts[self.active_account]["base_uri"]
            self.github_token = self.accounts[self.active_account]["github_token"]

if git:
    class RemoteUrlCommand(git.GitTextCommand):
        url_type = 'blob'
        allows_line_highlights = False
        # Operate on current branch by default; other values include 'default' to operate on the default branch defined
        # in GitHub.sublime-settings, and False to operate on the current HEAD of the current branch i.e. use a
        # permalink https://help.github.com/en/articles/getting-permanent-links-to-files.
        branch = 'current'

        def run(self, edit):
            if self.branch == "default":
                self.settings = sublime.load_settings("GitHub.sublime-settings")
                default_branch_setting = self.settings.get("default_branch")

                if default_branch_setting:
                    branch = default_branch_setting
                else:
                    # Get the path of the currently opened file
                    file_path = self.view.window().active_view().file_name()

                    # Get the list of folders in the project
                    folders = self.view.window().folders()

                    top_level_folder = None
                    for folder in folders:
                        if file_path.startswith(folder):
                            top_level_folder = folder
                            break

                    branch = (
                        subprocess.check_output(
                            "git -C %s symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'"%(top_level_folder),
                            stderr=subprocess.STDOUT,
                            shell=True,
                        )
                        .decode("utf-8")
                        .strip()
                    )
            else:
                # Get the current remote branch--useful whether we want to link directly to that
                # branch or to the branch's HEAD.
                branch = ""
            command = "git rev-parse --abbrev-ref --symbolic-full-name %s@{upstream}" % branch
            self.run_command(command.split(), self.done_rev_parse)

        def done_rev_parse(self, result):
            if "fatal:" in result:
                sublime.error_message(result)
                return

            remote, self.remote_branch = result.strip().split("/", 1)

            self.settings = sublime.load_settings("GitHub.sublime-settings")
            self.active_account = self.settings.get("active_account")
            self.accounts = self.settings.get("accounts")

            if not self.active_account:
                self.active_account = list(self.accounts.keys())[0]

            self.protocol = self.accounts[self.active_account].get("protocol", "https")
            # Override the remote with the user setting (if it exists)
            remote = self.accounts[self.active_account].get("remote", remote)

            command = "git ls-remote --get-url " + remote

            self.run_command(command.split(), self.done_remote)

        def done_remote(self, result):
            remote_loc = result.split()[0]
            repo_url = re.sub('^git(@|://)', self.protocol + '://', remote_loc)
            # Replace the "tld:" with "tld/"
            # https://github.com/bgreenlee/sublime-github/pull/49#commitcomment-3688312
            repo_url = re.sub(r'^(https?://[^/:]+):', r'\1/', repo_url)
            repo_url = re.sub(r'\.git$', '', repo_url)
            self.repo_url = repo_url
            self.run_command("git rev-parse --show-toplevel".split(), self.done_toplevel)

        # Get the repo's explicit toplevel path
        def done_toplevel(self, result):
            self.toplevel_path = result.strip()
            # get file path within repo
            absolute_path = self.view.file_name()
            # self.view.file_name() contains backslash on Windows instead of forwardslash
            absolute_path = absolute_path.replace('\\', '/')
            # we case-insensitive split because Windows
            relative_path = re.split(re.escape(self.toplevel_path), absolute_path, re.IGNORECASE).pop()

            line_nums = ""
            if self.allows_line_highlights:
                # if any lines are selected, the first of those
                non_empty_regions = [region for region in self.view.sel() if not region.empty()]
                if non_empty_regions:
                    selection = non_empty_regions[0]
                    (start_row, _) = self.view.rowcol(selection.begin())
                    (end_row, end_col) = self.view.rowcol(selection.end())
                    # If you select a single line (e.g., by using 'Expand selection to line'),
                    # the selection will actually end up as two lines, ending at column 0 of
                    # the second line. This accounts for that so that the final line is ignored.
                    if end_col == 0:
                        end_row -= 1
                    line_nums = "#L%s" % (start_row + 1)
                    if end_row > start_row:
                        line_nums += "-L%s" % (end_row + 1)
                elif self.settings.get("always_highlight_current_line"):
                    (current_row, _) = self.view.rowcol(self.view.sel()[0].begin())
                    line_nums = "#L%s" % (current_row + 1)

            self.relative_path = relative_path
            self.line_nums = line_nums

            if self.branch:
                self.generate_url()
            else:
                command = "git rev-parse " + self.remote_branch
                self.run_command(command.split(), self.done_remote_head)

        def done_remote_head(self, result):
            self.remote_head = result.strip()
            self.generate_url()

        def generate_url(self):
            if self.branch:
                remote_id = self.remote_branch
            else:
                remote_id = self.remote_head
            self.url = "%s/%s/%s%s%s" % (self.repo_url, self.url_type, remote_id, self.relative_path, self.line_nums)
            self.on_done()
else:
    class RemoteUrlCommand(sublime_plugin.TextCommand):
        def run(self, edit):
            sublime.error_message("I couldn't find the Git plugin. Please install it, restart Sublime Text, and try again.")


class OpenRemoteUrlCommand(RemoteUrlCommand):
    allows_line_highlights = True

    def run(self, edit):
        super(OpenRemoteUrlCommand, self).run(edit)

    def on_done(self):
        sublime.active_window().run_command('open_url', {'url': self.url})


class OpenRemoteUrlDefaultCommand(OpenRemoteUrlCommand):
    branch = "default"


class OpenRemoteUrlPermalinkCommand(OpenRemoteUrlCommand):
    branch = False


class CopyRemoteUrlCommand(RemoteUrlCommand):
    allows_line_highlights = True

    def run(self, edit):
        super(CopyRemoteUrlCommand, self).run(edit)

    def on_done(self):
        sublime.set_clipboard(self.url)
        sublime.status_message("Remote URL copied to clipboard")


class OpenPullCommand(RemoteUrlCommand):

    def run(self, edit):
        branch = ""
        command = "git rev-parse --abbrev-ref --symbolic-full-name ""@{upstream}"
        self.run_command(command.split(), self.generate_pr_url)

    def generate_pr_url(self, result):
        if "fatal:" in result:
            sublime.error_message(result)
            return

        remote, self.remote_branch = result.strip().split("/", 1)

        self.settings = sublime.load_settings("GitHub.sublime-settings")
        self.active_account = self.settings.get("active_account")
        self.accounts = self.settings.get("accounts")

        if not self.active_account:
            self.active_account = list(self.accounts.keys())[0]

        self.protocol = self.accounts[self.active_account].get(
            "protocol", "https")
        # Override the remote with the user setting (if it exists)
        remote = self.accounts[self.active_account].get("remote", remote)

        command = "git ls-remote --get-url " + remote

        self.run_command(command.split(), self.done_remote)

    def done_remote(self, result):
        remote_loc = result.split()[0]
        repo_url = re.sub('^git(@|://)', self.protocol + '://', remote_loc)
        # Replace the "tld:" with "tld/"
        # https://github.com/bgreenlee/sublime-github/pull/49#commitcomment-3688312
        repo_url = re.sub(r'^(https?://[^/:]+):', r'\1/', repo_url)
        repo_url = re.sub(r'\.git$', '', repo_url)
        self.repo_url = repo_url
        self.url = "%s/pull/%s" % (self.repo_url, self.remote_branch)
        self.on_done()

    def on_done(self):
        sublime.active_window().run_command('open_url', {'url': self.url})


class CopyRemoteUrlDefaultCommand(CopyRemoteUrlCommand):
    branch = "default"


class CopyRemoteUrlPermalinkCommand(CopyRemoteUrlCommand):
    branch = False


class BlameCommand(OpenRemoteUrlCommand):
    url_type = 'blame'


class BlameDefaultCommand(BlameCommand):
    branch = "default"


class BlamePermalinkCommand(BlameCommand):
    branch = False


class HistoryCommand(OpenRemoteUrlCommand):
    url_type = 'commits'
    allows_line_highlights = False


class HistoryDefaultCommand(HistoryCommand):
    branch = "default"


class HistoryPermalinkCommand(HistoryCommand):
    branch = False


class EditCommand(OpenRemoteUrlCommand):
    url_type = 'edit'
    allows_line_highlights = False


class EditDefaultCommand(EditCommand):
    branch = "default"


# GitHub only supports editing files on branches, so we don't define an `EditPermalinkCommand`.
