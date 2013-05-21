# adapted from https://github.com/wbond/sublime_package_control/blob/master/Package%20Control.py
import os.path
import subprocess


class BinaryNotFoundError(Exception):
    pass

class CommandExecutionError(Exception):
    def __init__(self, errorcode):
        self.errorcode = errorcode

    def __str__(self):
        return repr('An error has occurred while executing the command')

def find_binary(name):
    dirs = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin',
        '/sbin', '/bin']
    for dir in dirs:
        path = os.path.join(dir, name)
        if os.path.exists(path):
            return path

    raise BinaryNotFoundError('The binary ' + name + ' could not be ' + \
        'located')


def execute(args):
    proc = subprocess.Popen(args, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    output = proc.stdout.read()

    if proc.wait() == 0:
        return output

    raise CommandExecutionError(proc.returncode)
