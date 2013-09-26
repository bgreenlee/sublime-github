import sys
import os.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import re
import requests
from requests.status_codes import codes
try:
    import http.client as httplib
except ImportError:
    import httplib
import commandline
import sublime
from io import BytesIO
import logging

logging.basicConfig(format='%(asctime)s %(message)s')
logger = logging.getLogger()


class CurlSession(object):
    ERR_UNKNOWN_CODE = "Curl failed with an unrecognized code"
    CURL_ERRORS = {
        2: "Curl failed initialization.",
        5: "Curl could not resolve the proxy specified.",
        6: "Curl could not resolve the remote host.\n\nPlease verify that your Internet"
           " connection works properly."
    }

    class FakeSocket(BytesIO):
        def makefile(self, *args, **kw):
            return self

    def __init__(self, verify=None):
        self.verify = verify

    def _parse_http(self, text):
        # if the response text starts with a 302, skip to the next non-302 header
        text = str(text, encoding='utf-8')
        if re.match(r'^HTTP/.*?\s302 Found', text):
            m = re.search(r'(HTTP/\d+\.\d+\s(?!302 Found).*$)', text, re.S)
            if not m:
                raise Exception("Unrecognized response: %s" % text)
            else:
                text = m.group(1)

        # if the response text starts with a "200 Connection established" but continues with a 201,
        # skip the 200 header. This happens when using a proxy.
        #
        # e.g. HTTP/1.1 200 Connection established
        #       Via: 1.1 proxy
        #       Connection: Keep-Alive
        #       Proxy-Connection: Keep-Alive
        #
        #       HTTP/1.1 201 Created
        #       Server: GitHub.com
        #       ...
        #       Status: 201 Created
        #       ...
        if re.match(r'^HTTP/.*?\s200 Connection established', text):
            m = re.search(r'(HTTP/\d+\.\d+\s(?!200 Connection established).*$)', text, re.S)
            if not m:
                raise Exception("Unrecognized response: %s" % text)
            else:
                text = m.group(1)

        # remove Transfer-Encoding: chunked header, as it causes reading the response to fail
        # first do a quick check for it, so we can avoid doing the expensive negative-lookbehind
        # regex if we don't need it
        if "Transfer-Encoding: chunked" in text:
            # we do the negative-lookbehind to make sure we only strip the Transfer-Encoding
            # string in the header
            text = re.sub(r'(?<!\r\n\r\n).*?Transfer-Encoding: chunked\r\n', '', text, count=1)

        logger.debug("CurlSession - getting socket from %s" % text)
        socket = self.FakeSocket(text.encode())
        response = httplib.HTTPResponse(socket)
        response.begin()
        return response

    def _build_response(self, text):
        logger.debug("CurlSession: building response from %s" % text)
        raw_response = self._parse_http(text)
        response = requests.models.Response()
        response.encoding = 'utf-8'
        response.status_code = raw_response.status
        response.headers = dict(raw_response.getheaders())
        response._content = raw_response.read()
        return response

    def request(self, method, url, headers=None, params=None, data=None, auth=None, allow_redirects=False, config=None, proxies=None):
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
            for k, v in headers.items():
                curl_options.extend(['-H', "%s: %s" % (k, v)])
        if method in ('post', 'patch'):
            curl_options.extend(['-d', data])
        if method == 'patch':
            curl_options.extend(['-X', 'PATCH'])
        if params:
            url += '?' + '&'.join(['='.join([k, str(v)]) for k, v in params.items()])
        if proxies and proxies.get('https', None):
            curl_options.extend(['-x', proxies['https']])

        command = [curl] + curl_options + [url]

        logger.debug("CurlSession: invoking curl with %s" % command)
        try:
            command_response = commandline.execute(command)
        except commandline.CommandExecutionError as e:
            logger.error("Curl execution: %s" % repr(e))
            self._handle_curl_error(e.errorcode)
            return

        response = self._build_response(command_response)
        response.url = url
        return response

    def post(self, *args, **kwargs):
        return self.request("post", *args, **kwargs)

    def _handle_curl_error(self, error):
        sublime.error_message(
            self.CURL_ERRORS.get(error, "%s: %s" % (self.ERR_UNKNOWN_CODE, error)))


def session(verify=None, force_curl=False):
    if not force_curl and hasattr(httplib, "HTTPSConnection"):
        session = requests.Session()
        session.verify = verify
        return session
    else:  # try curl
        return CurlSession(verify=verify)
