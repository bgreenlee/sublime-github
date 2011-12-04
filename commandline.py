# adapted from https://github.com/wbond/sublime_package_control/blob/master/Package%20Control.py
import os.path
import subprocess


class BinaryNotFoundError(Exception):
    pass


class NonCleanExitError(Exception):
    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)


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
    returncode = proc.wait()
    if returncode != 0:
        raise NonCleanExitError(returncode)
    return output
