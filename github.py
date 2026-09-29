"""
GitHub API
"""
import json
import logging
from urllib.parse import urlencode

import sublime_requests as requests
from sublime_requests import ConnectionError

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
        "Raised if we get an empty response"
        pass

    def __init__(self, base_uri="https://api.github.com", token=None, debug=False, proxies=None):
        self.base_uri = base_uri
        self.token = token
        self.debug = debug
        self.proxies = proxies
        if debug:
            logger.setLevel(logging.DEBUG)

        self.rsession = requests.session()

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

        # The cache key includes query parameters (notably gist pagination).
        cache_url = url + (("&" if "?" in url else "?") + urlencode(params) if params else "")
        # Share the cache between commands, but never between accounts or pages.
        cache_key = (self.base_uri, self.token, cache_url)
        if method == 'get' and cache_key in self.etags:
            headers["If-None-Match"] = self.etags[cache_key]
        logger.debug("request: %s %s %s", method, url, params)

        try:
            resp = self.rsession.request(method, url,
                                         headers=headers,
                                         params=params,
                                         data=data,
                                         proxies=self.proxies,
                                         allow_redirects=True)
            if resp is None:
                raise self.NullResponseException("Empty response received.")
        except ConnectionError as e:
            raise self.ConnectionException(
                "Connection error, please verify your internet connection: %s" % e)

        logger.debug("response status: %s", resp.status_code)
        if resp.status_code in [requests.codes.OK,
                                requests.codes.CREATED,
                                requests.codes.FOUND,
                                requests.codes.CONTINUE]:
            if 'application/json' in resp.headers.get('Content-Type', ''):
                resp_data = json.loads(resp.text)
            else:
                resp_data = resp.text
            if method == 'get':  # cache the response
                etag = resp.headers.get('ETag')
                if etag:
                    self.etags[cache_key] = etag
                    self.cache[cache_key] = resp_data
            return resp_data
        elif resp.status_code == requests.codes.NOT_MODIFIED:
            etag = resp.headers.get('ETag', self.etags.get(cache_key))
            if etag == self.etags.get(cache_key) and cache_key in self.cache:
                return self.cache[cache_key]
            raise self.UnknownException("304 response without a cached Gist")
        elif resp.status_code == requests.codes.UNAUTHORIZED:
            raise self.UnauthorizedException()
        else:
            raise self.UnknownException("%d %s" % (resp.status_code, resp.text))

    def create_gist(self, description="", filename="", content="", public=False):
        return self.post("/gists", {"description": description,
                                    "public": public,
                                    "files": {filename: {"content": content}}})

    def get_gist(self, gist):
        data = self.get("/gists/" + gist["id"])
        return list(data["files"].values())[0]["content"]

    def update_gist(self, gist, content):
        filename = list(gist["files"].keys())[0]
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
