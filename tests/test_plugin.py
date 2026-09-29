import importlib.util
from contextlib import nullcontext
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request


PACKAGE = Path(__file__).resolve().parents[1]


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sublime = types.ModuleType("sublime")
        sublime.packages_path = lambda: str(PACKAGE.parent.parent)
        sublime.load_settings = lambda name: types.SimpleNamespace(get=lambda key, default=None: {"default_branch": "master", "accounts": {"GitHub": {"base_uri": "https://api.github.com"}}}.get(key, default))
        sublime.active_window = lambda: cls.window
        sublime.set_timeout = lambda callback, delay=0: callback()
        sublime.status_message = lambda message: None
        cls.errors = []
        sublime.error_message = lambda message: cls.errors.append(message)
        sublime_plugin = types.ModuleType("sublime_plugin")
        sublime_plugin.TextCommand = type("TextCommand", (), {})
        sublime_plugin.WindowCommand = type("WindowCommand", (), {})
        cls.window = types.SimpleNamespace(run_command=lambda name, args: setattr(cls, "opened_url", args["url"]))
        cls.modules = patch.dict(sys.modules, {"sublime": sublime, "sublime_plugin": sublime_plugin})
        cls.modules.start()
        sys.path.insert(0, str(PACKAGE))
        spec = importlib.util.spec_from_file_location("sublime_github", PACKAGE / "sublime_github.py")
        cls.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.plugin)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(PACKAGE))
        cls.modules.stop()

    def setUp(self):
        import github
        github.GitHubApi.etags.clear()
        github.GitHubApi.cache.clear()
        self.errors.clear()

    def test_commands_load_on_current_python(self):
        self.assertTrue(issubclass(self.plugin.BlameDefaultCommand, self.plugin.OpenRemoteUrlCommand))

    def test_gist_api_handles_responses_without_etag_and_unauthorized_tokens(self):
        import github
        import sublime_requests

        class Opener:
            def open(self, request, timeout):
                self.request = request
                if request.full_url.endswith("/gists/invalid"):
                    return HTTPError(request.full_url, 401, "", {"Content-Type": "application/json"},
                                     io.BytesIO(b'{"message":"Bad credentials"}'))
                return nullcontext(types.SimpleNamespace(
                    status=200, headers={"Content-Type": "application/json"}, url=request.full_url,
                    read=lambda: b'{"files":{}}',
                ))

        opener = Opener()
        with patch.object(sublime_requests, "build_opener", return_value=opener):
            api = github.GitHubApi(token="example")
            self.assertEqual(api.get("/gists/example"), {"files": {}})
            self.assertEqual(opener.request.get_header("Authorization"), "token example")
            with self.assertRaises(api.UnauthorizedException):
                api.get("/gists/invalid")

    def test_gist_requests_encode_parameters_and_keep_etags_per_account(self):
        import github
        import sublime_requests

        seen = []

        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                return nullcontext(types.SimpleNamespace(
                    status=200, headers={"Content-Type": "application/json", "ETag": '"one"'},
                    url=request.full_url, read=lambda: b'[]',
                ))

        with patch.object(sublime_requests, "build_opener", return_value=Opener()):
            first = github.GitHubApi(token="first")
            second = github.GitHubApi(token="second")
            first.get("/gists", params={"page": 1, "per_page": 100})
            first.get("/gists", params={"page": 2, "per_page": 100})
            second.get("/gists", params={"page": 1, "per_page": 100})
            first.get("/gists/example")
            second.get("/gists/example")

        self.assertEqual(parse_qs(urlsplit(seen[0].full_url).query), {"page": ["1"], "per_page": ["100"]})
        self.assertIsNone(seen[1].get_header("If-none-match"))
        self.assertIsNone(seen[2].get_header("If-none-match"))
        self.assertIsNone(seen[4].get_header("If-none-match"))

    def test_legacy_gist_token_is_migrated_without_losing_it(self):
        values = {
            "accounts": {"GitHub": {"base_uri": "https://api.github.com", "github_token": ""}},
            "github_token": "legacy-token",
        }
        settings = types.SimpleNamespace(
            get=lambda key, default=None: values.get(key, default),
            set=lambda key, value: values.__setitem__(key, value),
            erase=lambda key: values.pop(key),
        )
        with patch.object(sys.modules["sublime"], "load_settings", return_value=settings), \
             patch.object(sys.modules["sublime"], "save_settings", create=True):
            command = self.plugin.BaseGitHubCommand()
            command.run(None)

        self.assertEqual(command.github_token, "legacy-token")
        self.assertEqual(command.accounts["GitHub"]["github_token"], "legacy-token")
        self.assertEqual(command.gistapi.token, "legacy-token")

    def test_gist_etag_is_reused_only_for_the_same_request(self):
        import github
        import sublime_requests

        requests = []

        class Opener:
            def open(self, request, timeout):
                requests.append(request)
                if len(requests) == 2:
                    return HTTPError(request.full_url, 304, "", {}, io.BytesIO())
                return nullcontext(types.SimpleNamespace(
                    status=200, headers={"Content-Type": "application/json", "ETag": '"gist"'},
                    url=request.full_url, read=lambda: b'[{"id":"example"}]',
                ))

        with patch.object(sublime_requests, "build_opener", return_value=Opener()):
            api = github.GitHubApi(token="example")
            self.assertEqual(api.get("/gists", params={"page": 1}), [{"id": "example"}])
            self.assertEqual(github.GitHubApi(token="example").get("/gists", params={"page": 1}),
                             [{"id": "example"}])
        self.assertEqual(requests[1].get_header("If-none-match"), '"gist"')

    def test_redirect_does_not_send_pat_to_another_origin(self):
        import sublime_requests

        request = Request("https://api.github.com/gists/example", headers={"Authorization": "token secret"})
        redirect = sublime_requests.SafeRedirectHandler()
        cross_origin = redirect.redirect_request(request, None, 302, "", {},
                                                 "https://example.org/elsewhere")
        same_origin = redirect.redirect_request(request, None, 302, "", {},
                                                "https://api.github.com/gists/other")
        self.assertIsNone(cross_origin.get_header("Authorization"))
        self.assertEqual(same_origin.get_header("Authorization"), "token secret")

    def test_gist_creation_sends_json_with_token(self):
        import github
        import sublime_requests

        class Opener:
            def open(self, request, timeout):
                self.request = request
                return nullcontext(types.SimpleNamespace(
                    status=201, headers={"Content-Type": "application/json"},
                    url=request.full_url, read=lambda: b'{"id":"example"}',
                ))

        opener = Opener()
        with patch.object(sublime_requests, "build_opener", return_value=opener):
            self.assertEqual(github.GitHubApi(token="example").create_gist(
                filename="test.py", content="hello", public=False), {"id": "example"})
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertEqual(opener.request.get_header("Authorization"), "token example")
        self.assertEqual(json.loads(opener.request.data)["files"], {"test.py": {"content": "hello"}})

    def test_git_helper_runs_in_file_directory_without_changing_process_cwd(self):
        from sublime_github_support import git

        if not git.find_git():
            self.skipTest("git is not installed")
        with tempfile.TemporaryDirectory(prefix="sublime github ") as directory:
            subprocess.run([git.find_git(), "init", "-q", directory], check=True)
            file_path = os.path.join(directory, "example.py")
            Path(file_path).touch()
            command = git.GitTextCommand()
            command.view = types.SimpleNamespace(file_name=lambda: file_path, settings=lambda: types.SimpleNamespace(get=lambda key: None))
            completed = threading.Event()
            results = []
            original_cwd = os.getcwd()
            command.run_command(["git", "rev-parse", "--show-toplevel"],
                                lambda result: (results.append(result.strip()), completed.set()))
            self.assertTrue(completed.wait(5), "git callback did not run")
            self.assertEqual([os.path.realpath(path) for path in results], [os.path.realpath(directory)])
            self.assertEqual(os.getcwd(), original_cwd)

    def test_view_and_blame_detect_default_branch_and_include_selected_lines(self):
        class Region:
            def begin(self): return 9
            def end(self): return 20
            def empty(self): return False

        view = types.SimpleNamespace(
            file_name=lambda: "/repo/lib/file.rb",
            sel=lambda: [Region()],
            rowcol=lambda point: (1, 0) if point == 9 else (3, 1),
        )
        results = {
            "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "origin/feature/new-ui",
            "git symbolic-ref --quiet --short refs/remotes/origin/HEAD": "origin/main",
            "git remote get-url origin": "git@github.com:Giftly/China.git",
            "git rev-parse --show-toplevel": "/repo",
        }
        for command_type, url_type in (
            (self.plugin.OpenRemoteUrlDefaultCommand, "blob"),
            (self.plugin.BlameDefaultCommand, "blame"),
        ):
            command = command_type()
            command.view = view
            command.run_command = lambda args, callback: callback(results[" ".join(args)])
            command.run(None)
            self.assertEqual(self.opened_url, f"https://github.com/Giftly/China/{url_type}/main/lib/file.rb#L2-L4")

    def test_default_branch_works_without_upstream_on_current_branch(self):
        command = self.plugin.OpenRemoteUrlDefaultCommand()
        command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb", sel=lambda: [])
        responses = {
            "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "fatal: no upstream configured",
            "git symbolic-ref --quiet --short refs/remotes/origin/HEAD": "origin/main",
            "git remote get-url origin": "git@github.com:Giftly/China.git",
            "git rev-parse --show-toplevel": "/repo",
        }
        command.run_command = lambda args, callback: callback(responses[" ".join(args)])
        command.run(None)
        self.assertEqual(self.opened_url, "https://github.com/Giftly/China/blob/main/file.rb")

    def test_default_branch_falls_back_to_local_tracking_refs(self):
        for refs, expected in (("origin/main\norigin/master", "main"), ("origin/master", "master")):
            with self.subTest(refs=refs):
                command = self.plugin.OpenRemoteUrlDefaultCommand()
                command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb", sel=lambda: [])
                responses = {
                    "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "origin/feature/topic",
                    "git symbolic-ref --quiet --short refs/remotes/origin/HEAD": "",
                    "git for-each-ref --format=%(refname:short) refs/remotes/origin/main refs/remotes/origin/master": refs,
                    "git remote get-url origin": "git@github.com:Giftly/China.git",
                    "git rev-parse --show-toplevel": "/repo",
                }
                command.run_command = lambda args, callback: callback(responses[" ".join(args)])
                command.run(None)
                self.assertEqual(self.opened_url, f"https://github.com/Giftly/China/blob/{expected}/file.rb")

    def test_default_branch_uses_configured_remote_and_user_fallback_last(self):
        command = self.plugin.OpenRemoteUrlDefaultCommand()
        command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb", sel=lambda: [])
        calls = []
        responses = {
            "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "fatal: no upstream configured",
            "git symbolic-ref --quiet --short refs/remotes/fork/HEAD": "",
            "git for-each-ref --format=%(refname:short) refs/remotes/fork/main refs/remotes/fork/master": "",
            "git remote get-url fork": "git@github.com:Giftly/China.git",
            "git rev-parse --show-toplevel": "/repo",
        }
        command.run_command = lambda args, callback: (calls.append(args), callback(responses[" ".join(args)]))
        settings = types.SimpleNamespace(get=lambda key, default=None: {
            "accounts": {"GitHub": {"base_uri": "https://api.github.com", "remote": "fork"}},
            "default_branch": "develop",
        }.get(key, default))
        with patch.object(sys.modules["sublime"], "load_settings", return_value=settings):
            command.run(None)
        self.assertEqual(self.opened_url, "https://github.com/Giftly/China/blob/develop/file.rb")
        self.assertEqual([args[1] for args in calls], ["rev-parse", "symbolic-ref", "for-each-ref", "remote", "rev-parse"])

    def test_missing_default_branch_reports_how_to_recover(self):
        command = self.plugin.OpenRemoteUrlDefaultCommand()
        command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb")
        responses = {
            "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "origin/feature/topic",
            "git symbolic-ref --quiet --short refs/remotes/origin/HEAD": "",
            "git for-each-ref --format=%(refname:short) refs/remotes/origin/main refs/remotes/origin/master": "",
        }
        command.run_command = lambda args, callback: callback(responses[" ".join(args)])
        settings = types.SimpleNamespace(get=lambda key, default=None: {
            "accounts": {"GitHub": {"base_uri": "https://api.github.com"}},
        }.get(key, default))
        self.opened_url = None
        with patch.object(sys.modules["sublime"], "load_settings", return_value=settings):
            command.run(None)
        self.assertIsNone(self.opened_url)
        self.assertIn("Fetch the remote", self.errors[-1])

    def test_missing_remote_reports_error_instead_of_opening_invalid_link(self):
        command = self.plugin.OpenRemoteUrlDefaultCommand()
        command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb", sel=lambda: [])
        responses = {
            "git rev-parse --abbrev-ref --symbolic-full-name @{upstream}": "fatal: no upstream configured",
            "git symbolic-ref --quiet --short refs/remotes/origin/HEAD": "origin/main",
            "git remote get-url origin": "error: No such remote 'origin'",
        }
        command.run_command = lambda args, callback: callback(responses[" ".join(args)])
        self.opened_url = None
        command.run(None)
        self.assertIsNone(self.opened_url)
        self.assertIn("origin", self.errors[-1])

    def test_current_branch_without_upstream_still_reports_error(self):
        command = self.plugin.OpenRemoteUrlCommand()
        command.view = types.SimpleNamespace(file_name=lambda: "/repo/file.rb")
        command.run_command = lambda args, callback: callback("fatal: no upstream configured")
        command.run(None)
        self.assertIn("no upstream", self.errors[-1])


if __name__ == "__main__":
    unittest.main()
