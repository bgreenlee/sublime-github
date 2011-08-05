import os
import os.path
import subprocess
import httplib
import urllib
import sublime
import sublime_plugin

class GithubUser(object):
    "Encapsulates a Github user."
    def __init__(self, user, token):
        self.user = user
        self.token = token

    @classmethod
    def generate_from_environment(cls):
        """
        Return a GithubUser initialized with the user's github username and
        token from the GITHUB_USER and GITHUB_TOKEN environment variables,
        if set, otherwise get them from git config.

        @throws OSError if GITHUB_USER/TOKEN is not set and git is not in the PATH
        """
        user = os.environ.get('GITHUB_USER', None) or \
            subprocess.Popen(["git", "config", "--get", "github.user"],
                             stdout=subprocess.PIPE).communicate()[0].strip()
        token = os.environ.get('GITHUB_TOKEN', None) or \
            subprocess.Popen(["git", "config", "--get", "github.token"],
                             stdout=subprocess.PIPE).communicate()[0].strip()

        if not user and not token:
            return None

        return cls(user, token)


class GistUnauthorizedException(Exception):
    "Raised if we get a 401 from Github"
    pass


class GistCreationException(Exception):
    "Raised if we get a response code we don't recognize from Github"
    pass


class Gist(object):
    "Encapsulates a Github gist."
    ERR_CREATING = "Error creating gist: %s %s"

    def __init__(self, github_user, description, filename, content, public=False):
        self.github_user = github_user
        self.description = description
        self.filename = filename
        self.content = content
        self.public = public

    def create(self):
        """
        Create a gist on Github. Returns the url of the gist.

        @throws GistCreationException if there was an error creating the gist.
        """
        params = {
            "file_ext[gistfile1]": os.path.splitext(self.filename)[1] or ".txt",
            "file_name[gistfile1]": self.filename,
            "file_contents[gistfile1]": self.content,
            "description": self.description,
            "login": self.github_user.user,
            "token": self.github_user.token
            }
        if not self.public:
            params['action_button'] = 'private'
        conn = httplib.HTTPSConnection("gist.github.com")
        req = conn.request("POST", "/gists", urllib.urlencode(params))
        response = conn.getresponse()
        conn.close()
        if response.status == 302: # success
            gist_url = response.getheader("Location")
            return gist_url
        elif response.status == 401: # unauthorized
            raise GistUnauthorizedException()
        else:
            raise GistCreationException(self.ERR_CREATING % (response.status, response.reason))


class GistFromSelectionCommand(sublime_plugin.TextCommand):
    """
    Base class for creating a Github Gist from the current selection.
    """
    MSG_DESCRIPTION = "Gist description:"
    MSG_FILENAME = "Gist filename:"
    MSG_SUCCESS = "Gist created and url copied to the clipboard."
    ERR_NO_SELECTION = "Error: nothing selected."
    ERR_NO_USER_TOKEN = "You must configure your Github username and token.\n\n"\
        "See http://help.github.com/set-your-user-name-email-and-github-token/ "\
        "for more information."
    ERR_NO_GIT = "Couldn't find git in your PATH. Make sure it is in your "\
        "PATH, or set the GITHUB_USER and GITHUB_TOKEN environment variables."
    ERR_UNAUTHORIZED = "Your Github username or API token appears to be "\
        "incorrect. Please check them and try again.\n\n"\
        "See http://help.github.com/set-your-user-name-email-and-github-token/ "\
        "for more information."

    def run(self, edit):
        self.github_user = None
        self.description = None
        self.filename = None
        # check for empty selection
        if all([region.empty() for region in self.view.sel()]):
            sublime.error_message(self.ERR_NO_SELECTION)
            return
        # get github user and token
        try:
            self.github_user = GithubUser.generate_from_environment()
            if self.github_user:
                self.view.window().show_input_panel(self.MSG_DESCRIPTION, "", self.on_done, None, None)
            else:
                sublime.error_message(self.ERR_NO_USER_TOKEN)
        except OSError, e:
            sublime.error_message(self.ERR_NO_GIT)

    def get_filename(self):
        # use the current filename as the default
        current_filename = self.view.file_name() or "snippet.txt"
        filename = os.path.basename(current_filename)
        self.view.window().show_input_panel(self.MSG_FILENAME, filename,
            self.on_done, None, None)

    def on_done(self, value):
        "Callback for show_input_panel."
        if self.description is None:
            self.description = value
            # need to do this or the input panel doesn't show
            sublime.set_timeout(self.get_filename, 50)
        else:
            self.filename = value
            # get selected text
            text = "\n".join([self.view.substr(region) for region in self.view.sel()])
            gist = Gist(github_user=self.github_user,
                        description=self.description,
                        filename=self.filename,
                        content=text,
                        public=self.public)
            try:
                gist_url = gist.create()
                sublime.set_clipboard(gist_url)
                sublime.status_message(self.MSG_SUCCESS)
            except GistUnauthorizedException:
                sublime.error_message(self.ERR_UNAUTHORIZED)
            except GistCreationException, e:
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
