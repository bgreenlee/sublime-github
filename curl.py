# adapted from https://github.com/wbond/sublime_package_control/blob/master/Package%20Control.py
import commandline
import sublime


def post(url, data, tries=3):
    curl = commandline.find_binary('curl')
    command = [curl, '-f', '--user-agent', 'Sublime Github', '-s',
               '-d', data, url]

    while tries > 1:
        tries -= 1
        try:
            return commandline.execute(command)
        except (commandline.NonCleanExitError) as (e):
            if e.returncode == 22:
                error_string = 'HTTP error 404'
            elif e.returncode == 6:
                error_string = 'URL error host not found'
            else:
                print "%s: Downloading %s timed out, trying again" % (__name__, url)
                continue

            sublime.error_message("%s: %s %s posting %s ." %
                                  (__name__, error_message, error_string, url))
        break
    return False
