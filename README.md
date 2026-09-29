# Sublime GitHub

This is a plugin for the [Sublime Text](http://www.sublimetext.com/) text
editor that provides a number of useful commands for GitHub, including creating and browsing gists,
opening and editing files on GitHub, and bringing up the blame and commit history views.

## Installation

Install with Package Control (search for `sublime-github`), or place this folder at `Packages/sublime-github` (Preferences > Browse Packages opens `Packages`). Restart Sublime Text if the commands do not appear.

## Usage

Repository commands need `git` on the Sublime Text process PATH, but no separate Git plugin or GitHub token. Gist commands require a personal access token; see "Generating Your Own Access Token" below.

The following commands are available in the Command Palette:

* **GitHub: Switch Accounts**

    Switch to another configured GitHub account (see Adding Additional Accounts below)

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

**The following commands require a `git` executable on your PATH, but not the Git Sublime package.**

**Note:** These commands use the currently checked out branch to generate GitHub URLs. Each command also has a corresponding version, such as **GitHub: Blame (default branch)**, that always uses the default branch configured in
plugin settings, regardless of which branch is checked out locally. This default branch is set to **main**, and can be changed by editing the **default_branch** setting in Preferences > Package Settings > GitHub. All commands except **GitHub: Edit** have a corresponding "permalink" version too, like **GitHub: Blame (permalink)**, that uses the most recent commit on the current branch ([more info](https://help.github.com/en/articles/getting-permanent-links-to-files)).

* **GitHub: Open Remote URL in Browser**

    Open the current file's location in the repository in the browser. If you have any lines selected, they will be highlighted in the browser.  The default protocol is 'https'.  The default remote used is '' (no remote).  If you want to change either of those set them in your GitHub.sublime-settings file for your specific account.

* **GitHub: Copy Remote URL to Clipboard**

    Put the url of the current file's location in the repository into the clipboard. If you have any lines selected, they will be included in the URL and highlighted when opened in a browser.

* **GitHub: Blame**

    Open the GitHub blame view of the current file in the browser. If you have any lines selected, they will be highlighted in the browser.

* **GitHub: History**

    Open the GitHub commit history view of the current file in the browser.

* **GitHub: View**

    Alias for *GitHub: Open Remote URL in Browser*

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

Set `github_token` to a personal access token with Gist access for each account where you use Gist commands. Switching accounts does not generate a token. Repository links do not need one.

## Key Bindings

You can add your own keyboard shortcuts in Preferences -> Key Bindings - User. For example:

    [
        { "keys": ["ctrl+super+g", "ctrl+super+n"], "command": "public_gist_from_selection" },
        { "keys": ["ctrl+super+g", "ctrl+super+p","super+n"], "command": "private_gist_from_selection" },
        { "keys": ["ctrl+super+g", "ctrl+super+o"], "command": "open_gist_in_editor" },
        { "keys": ["ctrl+super+g", "ctrl+super+c"], "command": "open_gist_url" }
    ]

(Note that `ctrl+super+g` (^⌘G) conflicts with Sublime Text's Quick Find All, so adjust accordingly.)
Available commands can be seen in <https://github.com/bgreenlee/sublime-github/blob/master/Github.sublime-commands>.

## Issues

* Depending on the number of gists you have, there can be a considerable delay the first time your list of gists is fetched. Subsequent requests will be cached and should be a bit faster (although the GitHub API's ETags are currently not correct; once they fix that, it should speed things up). In the meantime, if there are gists that you open frequently, open them on GitHub and "Star" them, then access them via the Open/Copy Starred Gist commands.

## Generating Your Own Access Token

Create a [GitHub personal access token](https://github.com/settings/tokens) with Gist access. GitHub no longer allows plugins to create tokens from a username and password. In `Packages/User/GitHub.sublime-settings`, set the token for the account:

    {
        "accounts": {
            "GitHub": {
                "base_uri": "https://api.github.com",
                "github_token": "YOUR_TOKEN"
            }
        }
    }

Keep this file private. A token is not required for View, Blame, History, or other repository links.

## Configuring a proxy

If you are behind a proxy you can configure it for each account.

For example:

    "accounts":
    {
        "GitHub":
        {
            "base_uri": "https://api.github.com",
            "https_proxy": "..."
        }
    }

## Bugs and Feature Requests

<http://github.com/bgreenlee/sublime-github/issues>

## Copyright

Copyright &copy; 2011+ Brad Greenlee. See LICENSE for details.
