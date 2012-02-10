# Sublime GitHub

This is a plugin for the [Sublime Text 2](http://www.sublimetext.com/) text
editor that allows you to create and browse your [GitHub Gists](http://gist.github.com).

## Installation

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    git clone https://github.com/bgreenlee/sublime-github.git

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

Note that depending on the number of gists you have, there can be a considerable
delay before your list of gists appears. I'm hoping I can implement caching of
the list, but right now the GitHub API doesn't have any reliable mechanism for
that.

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

