# Sublime GitHub

This is a plugin for the [Sublime Text 2](http://www.sublimetext.com/) text
editor that provides a number of useful commands for GitHub, including creating and browsing gists,
opening and editing files on GitHub, and bringing up the blame and commit history views.

## Installation

**The easiest way to install is via the** [**Sublime Package Control**](http://wbond.net/sublime_packages/package_control) **plugin.**
Just open "Package Control: Install Package" in your Command Palette and search for
"sublime-github" (or, if you already have it installed, select "Package Control: Upgrade Package"
to upgrade).

To install it manually in a shell/Terminal (on OS X, Linux or Cygwin), via git:

    cd ~/"Library/Application Support/Sublime Text 2/Packages/" # location on OS X; will be different on Linux & Windows
    git clone https://github.com/bgreenlee/sublime-github.git

or, if you don't have git installed:

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    rm -rf bgreenlee-sublime-github*  # remove any old versions
    curl -L https://github.com/bgreenlee/sublime-github/tarball/master | tar xf -

The plugin should be picked up automatically. If not, restart Sublime Text.

## Usage

The first time you run one of the commands, it will ask you for your GitHub
username and password in order to create a GitHub API access token, which gets saved
in the Sublime GitHub user settings file. Your username and password are not
stored anywhere, but if you would rather generate the access token yourself, see
the "Generating Your Own Access Token" section below.

The following commands are available in the Command Palette:

* **GitHub: Switch Accounts**

    Switch to another GitHub account (see Adding Additional Accounts below)

* **GitHub: Private Gist from Selection**

	Create a private gist from the currently selected text (or, if nothing is selected,
	the contents of the active editor.

* **GitHub: Public Gist from Selection**

	Create a public gist from the currently selected text (or, if nothing is selected,
	the contents of the active editor.

* **GitHub: Copy Gist to Clipboard**

    Displays a quick select panel listing all of your gists, and selecting one will
    copy the contents of that gist to your clipboard.

* **GitHub: Copy Starred Gist to Clipboard**

    Displays a quick select panel listing only your starred gists, and selecting one will
    copy the contents of that gist to your clipboard.

* **GitHub: Open Gist in Editor**

    Displays a quick select panel listing all of your gists, and selecting one will
    open a new editor tab with the contents of that gist.

* **GitHub: Open Starred Gist in Editor**

    Displays a quick select panel listing only your starred gists, and selecting one will
    open a new editor tab with the contents of that gist.

* **GitHub: Open Gist in Browser**

    Displays a quick select panel listing all of your gists, and selecting one will
    open that gist in your default web browser.

* **GitHub: Open Starred Gist in Browser**

    Displays a quick select panel listing only your starred gists, and selecting one will
    open that gist in your default web browser.

* **GitHub: Update Gist**

    Update the gist open in the current editor.

**The following commands require the Git plugin, available through the Package Manager. After installing, restart Sublime Text.**

* **GitHub: Open Remote URL in Browser**

    Open the current file's location in the repository in the browser.

* **GitHub: Copy Remote URL to Clipboard**

    Put the url of the current file's location in the repository into the clipboard.

* **GitHub: Blame**

    Open the GitHub blame view of the current file in the browser

* **GitHub: History**

    Open the GitHub commit history view of the current file in the browser.

* **GitHub: Edit**

    Open the current file for editing on GitHub. I'm not sure why you'd want to do that, but it was easy enough to add.

## Adding Additional Accounts

If have multiple GitHub accounts, or have a private GitHub installation, you can add the other
accounts and switch between them whenever you like.

Go to the GitHub user settings file (Preferences -> Package Settings -> GitHub -> Settings - User),
and add another entry to the `accounts` dictionary. If it is another GitHub account, copy the
`base_uri` for the default GitHub entry (if you don't see it, you can get it from Preferences ->
Package Settings -> GitHub -> Settings - Default, or in the example below), and just give the
account a different name. If you're adding a private GitHub installation, the `base_uri` will be
whatever the base url is for your private GitHub, plus "/api/v3". For example:

    "accounts":
    {
        "GitHub":
        {
            "base_uri": "https://api.github.com",
            "github_token": "..."
        },
        "YourCo":
        {
            "base_uri": "https://github.yourco.com/api/v3",
            "github_token": ""
        }
    }

Don't worry about setting the `github_token`--that will be set for you automatically, after you
switch accounts (Shift-Cmd-P, "GitHub: Switch Accounts").

## Issues

* Linux requires the [curl](http://curl.haxx.se/) binary to be installed on your system (in one of:
`/usr/local/sbin`, `/usr/local/bin`, `/usr/sbin`, `/usr/bin`, `/sbin`, or `/bin`).

* Depending on the number of gists you have, there can be a considerable delay the first time
your list of gists is fetched. Subsequent requests will be cached and should be a bit faster
(although the GitHub API's ETags are currently not correct; once they fix that, it should speed
things up). In the meantime, if there are gists that you open frequently, open them on GitHub and
"Star" them, then access them via the Open/Copy Starred Gist commands.

* Setting the file type for syntax highlighting when opening a gist in the editor does not work
in Linux. I could get it to work with significant effort, so if you desperately want it, open
an issue.

## Generating Your Own Access Token

If you feel uncomfortable giving your GitHub username and password to the
plugin, you can generate a GitHub API access token yourself. Just open up
a Terminal window/shell (on OS X, Linux or Cygwin), and run:

    curl -u username -d '{"scopes":["gist"]}' https://api.github.com/authorizations

where `username` is your GitHub username. You'll be prompt for your password first. Then you'll get back
a response that includes a 40-digit "token" value (e.g. `6423ba8429a152ff4a7279d1e8f4674029d3ef87`).
Go to Sublime Text 2 -> Preferences -> Package Settings -> GitHub -> Settings - User,
and insert the token there. It should look like:

    {
        "github_token": "6423ba8429a152ff4a7279d1e8f4674029d3ef87"
    }

Restart Sublime.

That's it!

## Configuring a proxy

If you are behind a proxy you can configure it for each account.

Note that until a [bug](https://github.com/shazow/urllib3/pull/170) in urllib3 is fixed, in order to use a proxy you also have to force curl mode (Curl is required obviously).

For example:

    "accounts":
    {
        "GitHub":
        {
            "base_uri": "https://api.github.com",
            "https_proxy": "...",
            "force_curl": true
        }
    }

## Bugs and Feature Requests

<http://github.com/bgreenlee/sublime-github/issues>

## Copyright

Copyright &copy; 2011+ Brad Greenlee. See LICENSE for details.

