# Sublime Github

This is a plugin for the [Sublime Text 2](http://www.sublimetext.com/) text
editor that allows you to create public or private
[Github Gists](http://gist.github.com) from the currently selected text.

## Installation

    cd ~/"Library/Application Support/Sublime Text 2/Packages/"
    git clone https://github.com/bgreenlee/sublime-github.git

The plugin should be picked up automatically. If not, restart Sublime Text.

## Usage

First, your Github username and API token needs to be set. See
<http://help.github.com/set-your-user-name-email-and-github-token/> to see how
to do this. Then:

1. Select some text.
2. Bring up the Command Palette (&#8679;&#8984;P by default)
3. Start typing "Github", and select either "Private Gist from Selection" or
   "Public Gist from Selection"
4. At the bottom of your editor, you'll be prompted for a description. After
   entering that, you'll be prompted for a filename.
5. The url for your new gist will be copied to the clipboard.

## Bugs

<http://github.com/bgreenlee/sublime-github/issues>

## Copyright

Copyright &copy; 2011 Brad Greenlee. See LICENSE for details.

