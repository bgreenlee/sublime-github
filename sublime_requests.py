import sys
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import re
import requests
from requests.status_codes import codes
import httplib
import commandline
import sublime

from StringIO import StringIO
from httplib import HTTPResponse


class CurlSession(object):
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

    def request(self, method, url, headers=None, params=None, data=None, auth=None, allow_redirects=False, config=None):
        try:
            curl = commandline.find_binary('curl')
        except commandline.BinaryNotFoundError:
            sublime.error_message("I couldn't find \"curl\" on your system. Curl is required on Linux. Please install it and try again.")
            return

        curl_options = ['-i', '-L', '--user-agent', 'Sublime Github', '-s']
        if auth:
            curl_options.extend(['--user', "%s:%s" % auth])
        if self.verify:
            curl_options.extend(['--cacert', self.verify])
        if headers:
            for k, v in headers.iteritems():
                curl_options.extend(['-H', "%s: %s" % (k, v)])
        if method in ('post', 'patch'):
            curl_options.extend(['-d', data])
        if method == 'patch':
            curl_options.extend(['-X', 'PATCH'])
        if params:
            url += '?' + '&'.join(['='.join([k, str(v)]) for k, v in params.iteritems()])

        command = [curl] + curl_options + [url]

        response = self._build_response(commandline.execute(command))
        response.url = url
        return response

    def post(self, *args, **kwargs):
        return self.request("post", *args, **kwargs)


def session(verify=None, config=None):
    if hasattr(httplib, "HTTPSConnection"):
        return requests.session(verify=verify, config=config)
    else:  # try curl
        return CurlSession(verify=verify)
