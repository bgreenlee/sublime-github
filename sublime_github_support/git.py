"""Git support for repository links, independent of the Sublime Git package."""

import os
import shutil
import subprocess
import threading

import sublime
import sublime_plugin


def find_git():
    return shutil.which("git")


def git_root(directory):
    directory = os.path.realpath(directory)
    while directory:
        if os.path.exists(os.path.join(directory, ".git")):
            return directory
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


class GitTextCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        name = self.view.file_name()
        return bool(name and git_root(os.path.dirname(name)))

    def run_command(self, command, callback):
        directory = os.path.dirname(self.view.file_name())
        executable = find_git()
        if not executable:
            sublime.error_message("Git binary could not be found. Add git to Sublime Text's PATH.")
            return

        def run():
            try:
                result = subprocess.run(
                    [executable] + command[1:], cwd=directory, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, check=False,
                )
                output = result.stdout.decode("utf-8", errors="replace")
                sublime.set_timeout(lambda: callback(output), 0)
            except OSError as error:
                sublime.set_timeout(lambda: sublime.error_message("Git failed: %s" % error), 0)

        threading.Thread(target=run, daemon=True).start()
