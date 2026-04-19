"""Unit tests for memory-bridge/templates/sync.py.

Run: python -m unittest discover -s plugins/memory-bridge/skills/sync/tests -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
import unittest.mock as mock
from datetime import date
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SYNC_PATH = THIS_DIR.parent / "templates" / "sync.py"


def _load_sync_module():
    spec = importlib.util.spec_from_file_location(
        "memory_bridge_sync_under_test", SYNC_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync = _load_sync_module()


class TestResolvePythonInterpreter(unittest.TestCase):
    def test_nothing_resolves(self):
        with mock.patch.object(sync.shutil, "which", return_value=None):
            self.assertIsNone(sync.resolve_python_interpreter())

    def test_python3_present(self):
        def which(cmd):
            return "/usr/bin/python3" if cmd == "python3" else None

        with mock.patch.object(sync.shutil, "which", side_effect=which):
            self.assertEqual(sync.resolve_python_interpreter(), "python3")

    def test_python_reports_python3(self):
        def which(cmd):
            mapping = {"python3": None, "python": "/usr/bin/python", "py": None}
            return mapping.get(cmd)

        with mock.patch.object(sync.shutil, "which", side_effect=which), mock.patch.object(
            sync, "_is_python3", return_value=True
        ):
            self.assertEqual(sync.resolve_python_interpreter(), "python")

    def test_python_reports_python2_is_skipped(self):
        def which(cmd):
            mapping = {"python3": None, "python": "/usr/bin/python", "py": None}
            return mapping.get(cmd)

        with mock.patch.object(sync.shutil, "which", side_effect=which), mock.patch.object(
            sync, "_is_python3", return_value=False
        ):
            self.assertIsNone(sync.resolve_python_interpreter())

    def test_py_launcher_resolves(self):
        def which(cmd):
            mapping = {"python3": None, "python": None, "py": r"C:\Windows\py.exe"}
            return mapping.get(cmd)

        with mock.patch.object(sync.shutil, "which", side_effect=which), mock.patch.object(
            sync, "_py_launcher_has_python3", return_value=True
        ):
            self.assertEqual(sync.resolve_python_interpreter(), "py -3")

    def test_py_launcher_without_python3_does_not_resolve(self):
        def which(cmd):
            mapping = {"python3": None, "python": None, "py": r"C:\Windows\py.exe"}
            return mapping.get(cmd)

        with mock.patch.object(sync.shutil, "which", side_effect=which), mock.patch.object(
            sync, "_py_launcher_has_python3", return_value=False
        ):
            self.assertIsNone(sync.resolve_python_interpreter())


class _FakeHeaders:
    def __init__(self, items=None):
        self._items = list(items or [])

    def items(self):
        return list(self._items)


class _FakeResponse:
    def __init__(self, status=200, body=b'{"status":"ok"}', headers=None):
        self.status = status
        self._body = body
        self.headers = _FakeHeaders(headers)

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


class TestPostUserAgent(unittest.TestCase):
    def test_post_sets_memory_bridge_user_agent(self):
        captured = {}

        def fake_urlopen(req, timeout=30):
            captured["req"] = req
            return _FakeResponse()

        with mock.patch.object(sync.urllib.request, "urlopen", side_effect=fake_urlopen):
            status, body, headers = sync.post(
                "http://example.com/ingest", "secret", {"title": "x"}
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers, {})
        req = captured["req"]
        ua = req.get_header("User-agent")
        self.assertIsNotNone(ua)
        self.assertRegex(ua, r"^memory-bridge/")


class TestExplainHttpFailure(unittest.TestCase):
    def test_403_with_cf_ray_header_is_cloudflare(self):
        msg = sync.explain_http_failure(403, "Forbidden", {"cf-ray": "abc-LAX"})
        self.assertIn("Cloudflare", msg)
        self.assertIn("NOT an API-key", msg)

    def test_403_with_error_code_10xx_is_cloudflare(self):
        msg = sync.explain_http_failure(
            403, "<html>error code: 1010 cf site blocked</html>", {}
        )
        self.assertIn("Cloudflare", msg)

    def test_403_with_cloudflare_word_in_body_is_cloudflare(self):
        msg = sync.explain_http_failure(403, "Cloudflare Ray ID: deadbeef", {})
        self.assertIn("Cloudflare", msg)

    def test_403_without_cf_signals_is_auth(self):
        msg = sync.explain_http_failure(403, "API key rejected", {})
        self.assertNotIn("Cloudflare", msg)
        self.assertIn("API key is rejected", msg)

    def test_422_unchanged(self):
        msg = sync.explain_http_failure(422, "bad payload", {})
        self.assertIn("422 unprocessable", msg)
        self.assertIn("bad payload", msg)

    def test_500_unchanged(self):
        msg = sync.explain_http_failure(500, "", {})
        self.assertIn("500 internal", msg)


class TestCmdNormalGaps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        self.daily = self.root / ".memory-compiler" / "daily"
        self.daily.mkdir(parents=True)
        self.bridge = self.root / ".memory-bridge"
        self.bridge.mkdir()

        self._orig = {
            "DAILY_DIR": sync.DAILY_DIR,
            "CONFIG_PATH": sync.CONFIG_PATH,
            "ENV_PATH": sync.ENV_PATH,
            "STATE_PATH": sync.STATE_PATH,
            "_today": sync._today,
            "forward_day": sync.forward_day,
            "get_key": sync.get_key,
        }
        sync.DAILY_DIR = self.daily
        sync.CONFIG_PATH = self.bridge / "config.json"
        sync.ENV_PATH = self.bridge / ".env"
        sync.STATE_PATH = self.bridge / "last_forwarded_day"
        sync.get_key = lambda: "fake-key"

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(sync, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_daily(self, iso):
        (self.daily / f"{iso}.md").write_text(f"log for {iso}", encoding="utf-8")

    def _write_config(self, cfg):
        sync.CONFIG_PATH.write_text(json.dumps(cfg), encoding="utf-8")

    def _install_fake_forward(self, outcomes=None):
        calls = []
        mapping = outcomes or {}

        def fake(day, *, priority, title_prefix=""):
            calls.append(day)
            return mapping.get(day, 0)

        sync.forward_day = fake
        return calls

    def _set_today(self, d):
        sync._today = lambda: d

    def test_forwards_all_gapped_days_with_existing_state(self):
        for d in ("2026-04-15", "2026-04-17", "2026-04-19"):
            self._write_daily(d)
        sync.STATE_PATH.write_text("2026-04-14\n", encoding="utf-8")
        self._write_config({"url": "u", "project": "p", "subsystem": ""})

        calls = self._install_fake_forward()
        self._set_today(date(2026, 4, 20))

        rc = sync.cmd_normal()
        self.assertEqual(rc, 0)
        self.assertEqual(
            calls, [date(2026, 4, 15), date(2026, 4, 17), date(2026, 4, 19)]
        )
        self.assertEqual(
            sync.STATE_PATH.read_text(encoding="utf-8").strip(), "2026-04-19"
        )

    def test_fresh_install_applies_7_day_cap_when_no_installed_at(self):
        for d in ("2026-04-01", "2026-04-10", "2026-04-15", "2026-04-19"):
            self._write_daily(d)
        self._write_config({"url": "u", "project": "p", "subsystem": ""})

        calls = self._install_fake_forward()
        self._set_today(date(2026, 4, 20))

        rc = sync.cmd_normal()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [date(2026, 4, 15), date(2026, 4, 19)])

    def test_fresh_install_honors_installed_at(self):
        for d in ("2026-04-10", "2026-04-15", "2026-04-19"):
            self._write_daily(d)
        self._write_config(
            {
                "url": "u",
                "project": "p",
                "subsystem": "",
                "installed_at": "2026-04-16",
            }
        )

        calls = self._install_fake_forward()
        self._set_today(date(2026, 4, 20))

        rc = sync.cmd_normal()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [date(2026, 4, 19)])

    def test_stops_on_first_failure_advances_state_to_last_success(self):
        for d in ("2026-04-15", "2026-04-17", "2026-04-19"):
            self._write_daily(d)
        sync.STATE_PATH.write_text("2026-04-14\n", encoding="utf-8")
        self._write_config({"url": "u", "project": "p", "subsystem": ""})

        calls = self._install_fake_forward(outcomes={date(2026, 4, 17): 1})
        self._set_today(date(2026, 4, 20))

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = sync.cmd_normal()

        self.assertNotEqual(rc, 0)
        self.assertEqual(calls, [date(2026, 4, 15), date(2026, 4, 17)])
        self.assertEqual(
            sync.STATE_PATH.read_text(encoding="utf-8").strip(), "2026-04-15"
        )
        self.assertIn("forwarded 1 of 3 days", stderr.getvalue())
        self.assertIn("stopped at 2026-04-17", stderr.getvalue())

    def test_today_is_excluded(self):
        self._write_daily("2026-04-19")
        self._write_daily("2026-04-20")  # today
        sync.STATE_PATH.write_text("2026-04-18\n", encoding="utf-8")
        self._write_config({"url": "u", "project": "p", "subsystem": ""})

        calls = self._install_fake_forward()
        self._set_today(date(2026, 4, 20))

        rc = sync.cmd_normal()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [date(2026, 4, 19)])

    def test_no_candidates_is_silent_success(self):
        sync.STATE_PATH.write_text("2026-04-19\n", encoding="utf-8")
        self._write_config({"url": "u", "project": "p", "subsystem": ""})

        calls = self._install_fake_forward()
        self._set_today(date(2026, 4, 20))

        rc = sync.cmd_normal()
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
