import sublime
import os.path
import json
import sublime_requests as requests
import sys
import logging
from requests.exceptions import ConnectionError

logging.basicConfig(format='%(asctime)s %(message)s')
logger = logging.getLogger()


class GitHubApi(object):
    "Encapsulates the GitHub API"
    PER_PAGE = 100
    etags = {}
    cache = {}

    class UnauthorizedException(Exception):
        "Raised if we get a 401 from GitHub"
        pass

    class UnknownException(Exception):
        "Raised if we get a response code we don't recognize from GitHub"
        pass

    class ConnectionException(Exception):
        "Raised if we get a ConnectionError"
        pass

    class NullResponseException(Exception):
        "Raised if we get an empty response (i.e., CurlSession failure)"
        pass

    def __init__(self, base_uri="https://api.github.com", token=None, debug=False, proxies=None, force_curl=False):
        self.base_uri = base_uri
        self.token = token
        self.debug = debug
        self.proxies = proxies

        if debug:
            logger.setLevel(logging.DEBUG)

        # set up requests session with the root CA cert bundle
        cert_path = os.path.join(sublime.packages_path(), "sublime-github", "ca-bundle.crt")
        if not os.path.isfile(cert_path):
            logger.warning("Root CA cert bundle not found at %s! Not verifying requests." % cert_path)
            cert_path = None
        self.rsession = requests.session(verify=cert_path,
                                         config={'verbose': sys.stderr if self.debug else None},
                                         force_curl=force_curl)

    def get_token(self, username, password):
        auth_data = {
            "scopes": ["gist"],
            "note": "Sublime GitHub",
            "note_url": "https://github.com/bgreenlee/sublime-github"
        }
        resp = self.rsession.post(self.base_uri + "/authorizations",
                                  auth=(username, password),
                                  proxies=self.proxies,
                                  data=json.dumps(auth_data))
        if resp.status_code == requests.codes.CREATED:
            data = json.loads(resp.text)
            return data["token"]
        elif resp.status_code == requests.codes.UNAUTHORIZED:
            raise self.UnauthorizedException()
        else:
            raise self.UnknownException("%d %s" % (resp.status_code, resp.text))

    def post(self, endpoint, data=None, content_type='application/json'):
        return self.request('post', endpoint, data=data, content_type=content_type)

    def patch(self, endpoint, data=None, content_type='application/json'):
        return self.request('patch', endpoint, data=data, content_type=content_type)

    def get(self, endpoint, params=None):
        return self.request('get', endpoint, params=params)

    def request(self, method, url, params=None, data=None, content_type=None):
        if not url.startswith("http"):
            url = self.base_uri + url
        if data:
            data = json.dumps(data)

        headers = {"Authorization": "token %s" % self.token}

        if content_type:
            headers["Content-Type"] = content_type

        # add an etag to the header if we have one
        if method == 'get' and url in self.etags:
            headers["If-None-Match"] = self.etags[url]
        logger.debug("request: %s %s %s %s" % (method, url, headers, params))

        try:
            resp = self.rsession.request(method, url,
                                     headers=headers,
                                     params=params,
                                     data=data,
                                     proxies=self.proxies,
                                     allow_redirects=True)
            if not resp:
                raise self.NullResponseException("Empty response received.")
        except ConnectionError, e:
            raise self.ConnectionException("Connection error, "
                "please verify your internet connection: %s" % e)

        full_url = resp.url
        logger.debug("response: %s" % resp.headers)
        if resp.status_code in [requests.codes.OK,
                                requests.codes.CREATED,
                                requests.codes.FOUND,
                                requests.codes.CONTINUE]:
            if 'application/json' in resp.headers['content-type']:
                resp_data = json.loads(resp.text)
            else:
                resp_data = resp.text
            if method == 'get':  # cache the response
                etag = resp.headers['etag']
                self.etags[full_url] = etag
                self.cache[etag] = resp_data
            return resp_data
        elif resp.status_code == requests.codes.NOT_MODIFIED:
            return self.cache[resp.headers['etag']]
        elif resp.status_code == requests.codes.UNAUTHORIZED:
            raise self.UnauthorizedException()
        else:
            raise self.UnknownException("%d %s" % (resp.status_code, resp.text))

    def create_gist(self, description="", filename="", content="", public=False):
        return self.post("/gists", {"description": description,
                                    "public": public,
                                    "files": {filename: {"content": content}}})

    def update_gist(self, gist, content):
        filename = gist["files"].keys()[0]
        return self.patch("/gists/" + gist["id"],
                         {"description": gist["description"],
                          "files": {filename: {"content": content}}})

    def list_gists(self, starred=False):
        page = 1
        data = []
        # fetch all pages
        while True:
            endpoint = "/gists" + ("/starred" if starred else "")
            page_data = self.get(endpoint, params={'page': page, 'per_page': self.PER_PAGE})
            data.extend(page_data)
            if len(page_data) < self.PER_PAGE:
                break
            page += 1
        return data
