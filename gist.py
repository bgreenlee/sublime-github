import os
import subprocess
import json
import urllib
import urllib2
import base64
import sublime, sublime_plugin

class Gist(object):
    """
    Encapsulates a Github gist.
    """
    def __init__(self, description, filename, content, public=False):
        self.description = description
        self.filename = filename
        self.content = content
        self.public = public

    def __str__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            "description": self.description,
            "public": self.public,
            "files": {
                self.filename: {
                    "content": self.content
                }
            }
        })

class GistFromSelectionCommand(sublime_plugin.TextCommand):
    """
    Base class for creating a Github Gist from the current selection.
    """
    GITHUB_URL = "https://api.github.com"

    def run(self, edit):
        self.description = None
        self.filename = None
        # check for empty selection
        if all([region.empty() for region in self.view.sel()]):
            sublime.error_message("Error: nothing selected.")
            return
        # get github user and token
        self.github_creds = self.get_github_creds()
        if self.github_creds:
            self.view.window().show_input_panel("Gist description", "", self.on_done, None, None)

    def get_github_creds(self):
        """
        Get the user's github username and token from the GITHUB_USER and
        GITHUB_TOKEN environment variables, if set, otherwise get them from
        git config.
        """
        try:
            user = os.environ.get('GITHUB_USER', None) or \
                subprocess.Popen(["git", "config", "--get", "github.user"],
                                 stdout=subprocess.PIPE).communicate()[0].strip()
            token = os.environ.get('GITHUB_TOKEN', None) or \
                subprocess.Popen(["git", "config", "--get", "github.token"],
                                 stdout=subprocess.PIPE).communicate()[0].strip()
        except OSError, e:
            sublime.error_message("Couldn't find git in your PATH. Make sure "
            "it is in your PATH, or set the GITHUB_USER and GITHUB_TOKEN "
            "environment variables.")
            return None

        if not user or not token:
            sublime.error_message("You must configure your Github username and "
            "token. See http://help.github.com/set-your-user-name-email-and-github-token/.")
            return None

        return (user, token)

    def get_filename(self):
        # get extension of current file
        extension = os.path.splitext(self.view.file_name())[1] or ".txt"
        self.view.window().show_input_panel("Gist filename", 
            "snippet" + extension, self.on_done, None, None)

    def on_done(self, value):
        if self.description is None:
            self.description = value
            # need to do this or the input panel doesn't show
            sublime.set_timeout(self.get_filename, 50)
        else:
            self.filename = value
            # get selected text
            text = ''.join([self.view.substr(region) for region in self.view.sel()])
            gist = Gist(self.description, self.filename, text, public=self.public)
            self.create_gist(gist)

    def create_gist(self, gist):
        req = urllib2.Request(self.GITHUB_URL+"/gists", data=str(gist))
        auth_string = base64.encodestring("%s:%s" % self.github_creds).replace("\n","")
        req.add_header("Authorization", "Basic %s" % auth_string)
        try:
            res = urllib2.urlopen(req)
            json_res = json.loads(res.read())
            sublime.set_clipboard(json_res['html_url'])
            sublime.status_message("Gist created and url copied to the clipboard.")
        except urllib2.URLError, e:
            if e.code == 401:
                error_msg = "Sorry, it appears your credentials were incorrect. "
                "Please check your username and password and try again."
            else:
                error_msg = "Sorry, there was an error creating your gist: %s %s" % (e.code, e.read())
            sublime.error_message(error_msg)

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
