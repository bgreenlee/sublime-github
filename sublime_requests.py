"""Small GitHub HTTP client using the Python standard library."""

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class ConnectionError(Exception):
    pass


class codes:
    OK = 200
    CREATED = 201
    FOUND = 302
    CONTINUE = 100
    NOT_MODIFIED = 304
    UNAUTHORIZED = 401


class Response:
    def __init__(self, response):
        self.status_code = getattr(response, "status", None) or response.code
        self.headers = response.headers
        self.url = response.url
        self.text = response.read().decode("utf-8")


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        redirected = super().redirect_request(request, fp, code, message, headers, new_url)
        original = urlsplit(request.full_url)
        target = urlsplit(new_url)
        if (original.scheme.lower(), original.netloc.lower()) != (target.scheme.lower(), target.netloc.lower()):
            redirected.remove_header("Authorization")
        return redirected


class Session:
    def request(self, method, url, headers=None, params=None, data=None, proxies=None, allow_redirects=True, auth=None):
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params)
        if auth:
            raise ValueError("GitHub password authentication is no longer supported; configure a personal access token")
        request = Request(url, data=data.encode("utf-8") if isinstance(data, str) else data,
                          headers={"User-Agent": "Sublime GitHub", **(headers or {})},
                          method=method.upper())
        proxy_settings = {key: value for key, value in (proxies or {}).items() if value}
        opener = build_opener(ProxyHandler(proxy_settings or None), SafeRedirectHandler())
        try:
            with opener.open(request, timeout=20) as response:
                return Response(response)
        except HTTPError as error:
            with error:
                return Response(error)
        except URLError as error:
            raise ConnectionError(str(error)) from error


def session():
    return Session()
