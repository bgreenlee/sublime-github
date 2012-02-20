import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import re
import requests
from requests.status_codes import codes
import httplib
import commandline

from StringIO import StringIO
from httplib import HTTPResponse


class CurlSession(object):
    class CurlException(Exception):
        pass

    class FakeSocket(StringIO):
        def makefile(self, *args, **kw):
            return self

    def __init__(self, verify=None):
        self.verify = verify

    def _parse_http(self, text):
        # if the response text starts with a 302, skip to the next non-302 header
        if re.match(r'^HTTP/.*?\s302 Found', text):
            m = re.search(r'(HTTP/\d+\.\d+\s(?!302 Found).*$)', text, re.S)
            if not m:
                raise Exception("Unrecognized response: %s" % text)
            else:
                text = m.group(1)
        socket = self.FakeSocket(text)
        response = HTTPResponse(socket)
        response.begin()
        return response

    def _build_response(self, text):
        raw_response = self._parse_http(text)
        response = requests.models.Response()
        response.encoding = 'utf-8'
        response.status_code = raw_response.status
        response.headers = dict(raw_response.getheaders())
        response._content = raw_response.read()
        return response

    def request(self, method, url, headers=None, params=None, data=None, auth=None, allow_redirects=False):
        curl = commandline.find_binary('curl')
        curl_options = ['-i', '-L', '-f', '--user-agent', 'Sublime Github', '-s']
        if auth:
            curl_options.extend(['--user', "%s:%s" % auth])
        if self.verify:
            curl_options.extend(['--cacert', self.verify])
        if headers:
            for k, v in headers.iteritems():
                curl_options.extend(['-H', "%s: %s" % (k, v)])
        if method == 'post':
            curl_options.extend(['-d', data])
        if params:
            url += '?' + '&'.join(['='.join([k, str(v)]) for k, v in params.iteritems()])

        command = [curl] + curl_options + [url]

        try:
            response = self._build_response(commandline.execute(command))
            response.url = url
            return response
        except commandline.NonCleanExitError, e:
            error_string = ''
            if e.returncode == 22:
                error_string = 'HTTP error 404'
            elif e.returncode == 6:
                error_string = 'URL error host not found'
            else:
                print "%s: Downloading %s timed out, trying again" % (__name__, url)

            raise self.CurlException("%s: %s %s %s %s" % (__name__, e, error_string, method, url))

        return False

    def post(self, *args, **kwargs):
        return self.request("post", *args, **kwargs)

def session(verify=None):
    if hasattr(httplib, "HTTPSConnection"):
        return requests.session(verify=verify)
    else:  # try curl
        return CurlSession(verify=verify)
