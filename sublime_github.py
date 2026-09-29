"""
SublimeGitHub commands
"""
import os
import os.path
import sys
import re
import logging as logger
import sublime
import sublime_plugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from github import GitHubApi

VERSION = "2.0.1"

from sublime_github_support import git


logger.basicConfig(format='[sublime-github] %(levelname)s: %(message)s')


class BaseGitHubCommand(sublime_plugin.TextCommand):
    """
    Base class for all GitHub commands. Handles getting an auth token.
    """
    ERR_NO_USER_TOKEN = ("Configure a GitHub personal access token with Gist access "
                         "as github_token in GitHub.sublime-settings to use Gist commands.")
    ERR_UNAUTHORIZED_TOKEN = ("Your GitHub Gist token was rejected. Update github_token "
                              "in GitHub.sublime-settings.")

    def run(self, edit):
        self.settings = sublime.load_settings("GitHub.sublime-settings")
        self.accounts = self.settings.get("accounts")
        self.active_account = self.settings.get("active_account")
        if not self.active_account:
            self.active_account = list(self.accounts.keys())[0]
        self.github_token = self.accounts[self.active_account]["github_token"]
        if not self.github_token:
            self.github_token = self.settings.get("github_token")
            if self.github_token:
                # migrate to new structure
                self.accounts[self.active_account]["github_token"] = self.github_token
                self.settings.set("accounts", self.accounts)
                self.settings.erase("github_token")
                sublime.save_settings("GitHub.sublime-settings")
        self.base_uri = self.accounts[self.active_account]["base_uri"]
        self.debug = self.settings.get('debug')

        self.proxies = {'https': self.accounts[self.active_account].get("https_proxy", None)}
        self.gistapi = GitHubApi(self.base_uri, self.github_token, debug=self.debug,
                                 proxies=self.proxies)

    def get_token(self):
        sublime.error_message(self.ERR_NO_USER_TOKEN)


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
        except GitHubApi.UnknownException as e:
            sublime.error_message(str(e))

    def on_done(self, idx):
        if idx == -1:
            return
        gist = self.gists[idx]
        filename = list(gist["files"].keys())[0]
        content = self.gistapi.get_gist(gist)
        if self.open_in_editor:
            new_view = self.view.window().new_file()
            syntax = sublime.find_syntax_for_file(filename)
            if syntax:
                new_view.assign_syntax(syntax)

            # insert the gist
            new_view.run_command("insert_text", {'text': content})
            new_view.set_name(filename)
            new_view.settings().set('gist', gist)
        elif self.copy_gist_id:
            sublime.set_clipboard(gist["html_url"])
        else:
            sublime.set_clipboard(content)
            sublime.status_message(self.MSG_SUCCESS % filename)


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
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
        except (GitHubApi.UnknownException, GitHubApi.ConnectionException) as e:
            sublime.error_message(str(e))

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
            self.get_token()

    def update(self):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        try:
            updated_gist = self.gistapi.update_gist(self.gist, text)
            sublime.set_clipboard(updated_gist["html_url"])
            sublime.status_message(self.MSG_SUCCESS)
        except GitHubApi.UnauthorizedException:
            sublime.error_message(self.ERR_UNAUTHORIZED_TOKEN)
        except GitHubApi.UnknownException as e:
            sublime.error_message(str(e))


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
            self.run_command(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                self.done_rev_parse,
            )

        def done_rev_parse(self, result):
            self.settings = sublime.load_settings("GitHub.sublime-settings")
            self.active_account = self.settings.get("active_account")
            self.accounts = self.settings.get("accounts")
            if not self.active_account:
                self.active_account = list(self.accounts.keys())[0]

            self.protocol = self.accounts[self.active_account].get("protocol", "https")
            configured_remote = self.accounts[self.active_account].get("remote")
            if "fatal:" in result:
                if self.branch == "default":
                    remote = "origin"
                elif self.branch is False:
                    if configured_remote:
                        self.remote = configured_remote
                        self.fetch_remote_url()
                    else:
                        self.run_command(["git", "remote"], self.done_remote_list)
                    return
                else:
                    sublime.error_message(result)
                    return
            else:
                remote, self.remote_branch = result.strip().split("/", 1)

            self.remote = configured_remote or remote
            if self.branch == "default":
                self.run_command(
                    ["git", "symbolic-ref", "--quiet", "--short", f"refs/remotes/{self.remote}/HEAD"],
                    self.done_default_branch,
                )
            else:
                self.fetch_remote_url()

        def done_default_branch(self, result):
            branch = result.strip()
            if branch.startswith(self.remote + "/"):
                self.remote_branch = branch[len(self.remote) + 1:]
                self.fetch_remote_url()
            else:
                self.run_command(
                    ["git", "for-each-ref", "--format=%(refname:short)",
                     f"refs/remotes/{self.remote}/main", f"refs/remotes/{self.remote}/master"],
                    self.done_default_candidates,
                )

        def done_remote_list(self, result):
            remotes = result.splitlines()
            if len(remotes) != 1:
                sublime.error_message("Set a remote in GitHub settings to create a permalink without an upstream branch.")
                return
            self.remote = remotes[0]
            self.fetch_remote_url()

        def done_default_candidates(self, result):
            refs = set(result.splitlines())
            for branch in ("main", "master"):
                if f"{self.remote}/{branch}" in refs:
                    self.remote_branch = branch
                    self.fetch_remote_url()
                    return

            self.remote_branch = self.settings.get("default_branch")
            if self.remote_branch:
                self.fetch_remote_url()
            else:
                sublime.error_message(f"No default branch found for {self.remote}. Fetch the remote or configure default_branch.")

        def fetch_remote_url(self):
            # Unlike ls-remote --get-url, this fails for a missing remote instead of returning its name.
            self.run_command(["git", "remote", "get-url", self.remote], self.done_remote)

        def done_remote(self, result):
            if not result.strip() or result.lstrip().startswith(("fatal:", "error:")):
                sublime.error_message("Cannot resolve Git remote %s: %s" % (self.remote, result.strip()))
                return
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
            relative_path = "/" + os.path.relpath(absolute_path, self.toplevel_path).replace('\\', '/')

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
                self.run_command(["git", "rev-parse", "HEAD"], self.done_head)

        def done_head(self, result):
            if not result.strip() or result.lstrip().startswith(("fatal:", "error:")):
                sublime.error_message("Cannot resolve HEAD: %s" % result.strip())
                return
            self.head = result.strip()
            self.run_command(
                ["git", "branch", "--remotes", "--contains", self.head, "--format=%(refname:short)"],
                self.done_remote_branches,
            )

        def done_remote_branches(self, result):
            if not any(branch.startswith(self.remote + "/") for branch in result.splitlines()):
                sublime.error_message("Push this commit to %s (or fetch its branches) before creating a permalink." % self.remote)
                return
            self.generate_url()

        def generate_url(self):
            if self.branch:
                remote_id = self.remote_branch
            else:
                # Use the commit checked out locally, including when HEAD is detached.
                remote_id = self.head
            self.url = "%s/%s/%s%s%s" % (self.repo_url, self.url_type, remote_id, self.relative_path, self.line_nums)
            self.on_done()


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
