# Sublime GitHub

This is a plugin for the [Sublime Text 2](http://www.sublimetext.com/) text
editor that allows you to create and browse your [GitHub Gists](http://gist.github.com).

## Installation

The easiest way to install is via the [Sublime Package Control](http://wbond.net/sublime_packages/package_control)
plugin. Just open "Package Control: Install Package" in your Command Palette and search for
"sublime-github" (or, if you already have it installed, select "Package Control: Upgrade Package"
to upgrade).

To install it manually in a shell/Terminal (on OS X or Linux), via git:

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    git clone https://github.com/bgreenlee/sublime-github.git

or, if you don't have git installed:

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    rm -rf bgreenlee-sublime-github*  # remove any old versions
    curl -L https://github.com/bgreenlee/sublime-github/tarball/gist-browsing | tar xf -

The plugin should be picked up automatically. If not, restart Sublime Text.

## Usage

The first time you run one of the commands, it will ask you for your GitHub
username and password in order to create a GitHub API access token, which gets saved
in the Sublime GitHub user settings file. Your username and password are not
stored anywhere, but if you would rather generate the access token yourself, see
the "Generating Your Own Access Token" section below.

The following commands are available in the Command Palette:

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

* **GitHub: Open Starred Gist in Editor**

    Displays a quick select panel listing only your starred gists, and selecting one will
    open that gist in your default web browser.


## Issues

* Linux requires the [curl](http://curl.haxx.se/) binary to be installed on your system (in one of:
`/usr/local/sbin`, `/usr/local/bin`, `/usr/sbin`, `/usr/bin`, `/sbin`, or `/bin`).

* Depending on the number of gists you have, there can be a considerable delay the first time
your list of gists is fetched. Subsequent requests will be cached and should be a bit faster
(although the GitHub API's ETags are currently not correct; once that fix that, it should speed
things up). In the meantime, if there are gists that you open frequently, open them on GitHub and
"Star" them, then access them via the Open/Copy Starred Gist commands.

* Setting the file type for syntax highlighting when opening a gist in the editor does not work
in Linux. I could get it to work with significant effort, so if you desperately want it, open
an issue.

## Generating Your Own Access Token

If you feel uncomfortable giving your GitHub username and password to the
plugin, you can generate a GitHub API access token yourself. Just open up
a Terminal window/shell (Windows users, you're on your own here), and run:

    curl -u "username:password" -d '{"scopes":["gist"]}' https://api.github.com/authorizations

where `username` and `password` are your GitHub credentials. You'll get back
a JSON response that includes a 40-digit "token" value (e.g. `6423ba8429a152ff4a7279d1e8f4674029d3ef87`).
Go to Sublime Text 2 -> Preferences -> Package Settings -> GitHub -> Settings - User,
and insert the token there. It should look like:

    {
        "github_token": "6423ba8429a152ff4a7279d1e8f4674029d3ef87"
    }

That's it!

## Bugs and Feature Requests

<http://github.com/bgreenlee/sublime-github/issues>

## Copyright

Copyright &copy; 2011+ Brad Greenlee. See LICENSE for details.

