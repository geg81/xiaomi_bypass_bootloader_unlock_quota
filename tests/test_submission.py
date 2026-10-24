"""Test single-request controls with synthetic data and no network access."""
from datetime import datetime, timezone
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import preflight as p
import submission as s

TOKEN = "test_only_token_123456789"


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / "state"
        self.addCleanup(self.temp.cleanup)
        self.network = patch("socket.socket", side_effect=AssertionError("Live network is forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def run_attempt(self, **kwargs):
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.object(s, "check_account", return_value="eligible"), patch.object(s, "sample_clock", return_value=p.ClockSample(1792830000, 100, 0, .05)), patch.object(s.time, "monotonic", return_value=100):
            return s.single_request(TOKEN, s.CONFIRMATION, directory=self.directory, **kwargs)

    def test_live_gate_blocks_before_input_and_network(self):
        with patch("builtins.input", side_effect=AssertionError("Input used")), patch.object(p.getpass, "getpass", side_effect=AssertionError("Token read")), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(p.main(["--submit-once"]), 2)
        with self.assertRaises(p.CheckError):
            s.single_request(TOKEN, s.CONFIRMATION, directory=self.directory)
        self.assertFalse(self.directory.exists())

    def test_confirmation_required(self):
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), self.assertRaises(p.CheckError):
            s.single_request(TOKEN, "no", directory=self.directory)
        self.assertFalse(self.directory.exists())

    def test_transport_gate_blocks_direct_call(self):
        with self.assertRaises(p.CheckError):
            s._post_once(TOKEN)

    def test_cli_reports_unknown_without_secret_or_false_success(self):
        output = io.StringIO()
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.dict("os.environ", {"XIAOMI_SERVICE_TOKEN": TOKEN}), patch("builtins.input", return_value=s.CONFIRMATION), patch.object(s, "single_request", return_value="outcome_unknown") as attempt, contextlib.redirect_stdout(output):
            self.assertEqual(p.main(["--submit-once"]), 3)
        attempt.assert_called_once()
        self.assertIn("outcome_unknown", output.getvalue())
        self.assertNotIn(TOKEN, output.getvalue())
        self.assertNotIn("No application was submitted", output.getvalue())

    @patch.object(s, "_post_once", return_value="outcome_unknown")
    def test_attempt_record_prevents_restart_and_token_change(self, post):
        self.assertEqual(self.run_attempt(), "outcome_unknown")
        self.assertTrue((self.directory / "attempt.json").exists())
        record = (self.directory / "attempt.json").read_text()
        self.assertNotIn(TOKEN, record)
        self.assertEqual(json.loads(record)["state"], "outcome_unknown")
        with self.assertRaises(p.CheckError):
            self.run_attempt()
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), self.assertRaises(p.CheckError):
            s.single_request("a_different_token_value", s.CONFIRMATION, directory=self.directory)
        post.assert_called_once()

    def test_lock_stops_second_process(self):
        code = "from pathlib import Path; import submission as s; import sys;\nwith s.attempt_lock(Path(sys.argv[1])): pass"
        with s.attempt_lock(self.directory):
            result = subprocess.run([sys.executable, "-c", code, str(self.directory)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.directory / "active.lock").exists())

    def test_crash_lock_stays_closed(self):
        self.directory.mkdir()
        (self.directory / "active.lock").mkdir()
        with self.assertRaises(p.CheckError):
            with s.attempt_lock(self.directory):
                self.fail("Stale lock accepted")
        self.assertTrue((self.directory / "active.lock").exists())

    @patch.object(s, "_post_once")
    def test_record_is_saved_before_transport(self, post):
        def inspect_record(token):
            self.assertEqual(json.loads((self.directory / "attempt.json").read_text())["state"], "outcome_unknown")
            return "outcome_unknown"
        post.side_effect = inspect_record
        self.run_attempt()
        post.assert_called_once()

    @patch.object(s, "_post_once")
    def test_disk_failure_blocks_transport(self, post):
        with patch.object(s.os, "fsync", side_effect=OSError(TOKEN)), self.assertRaises(p.CheckError):
            self.run_attempt()
        post.assert_not_called()
        self.assertTrue((self.directory / "attempt.json").exists())

    @patch.object(s, "_post_once", side_effect=KeyboardInterrupt)
    def test_interrupt_keeps_unknown_record(self, post):
        self.assertEqual(self.run_attempt(), "outcome_unknown")
        self.assertTrue((self.directory / "attempt.json").exists())

    @patch.object(s, "_post_once")
    def test_ineligible_accounts_stop(self, post):
        for state in ("blocked", "token_rejected", "unknown", "account_too_new", "already_approved"):
            with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.object(s, "check_account", return_value=state), patch.object(s, "sample_clock") as clock, self.assertRaises(p.CheckError):
                s.single_request(TOKEN, s.CONFIRMATION, directory=self.directory)
            clock.assert_not_called()
        post.assert_not_called()
        self.assertFalse((self.directory / "attempt.json").exists())

    @patch.object(s, "_post_once")
    def test_time_failures_stop(self, post):
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.object(s, "check_account", return_value="eligible"):
            with patch.object(s, "sample_clock", side_effect=p.CheckError("NTP failed")), self.assertRaises(p.CheckError):
                s.single_request(TOKEN, s.CONFIRMATION, directory=self.directory)
            with patch.object(s, "sample_clock", return_value=p.ClockSample(1792830000, 100, 0, .05)), patch.object(s.time, "monotonic", return_value=106), self.assertRaises(p.CheckError):
                s.single_request(TOKEN, s.CONFIRMATION, directory=self.directory)
        for stamp in (1792829999, 1792830061):
            with self.assertRaises(p.CheckError):
                self.run_attempt(target=datetime.fromtimestamp(stamp, timezone.utc))
        post.assert_not_called()

    @patch.object(s, "_post_once", return_value="outcome_unknown")
    def test_scheduled_request_uses_monotonic_time(self, post):
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.object(s, "check_account", return_value="eligible"), patch.object(s, "sample_clock", return_value=p.ClockSample(1792830000, 100, 0, .05)), patch.object(s.time, "monotonic", side_effect=[100, 100.25, 100.5, 100.5]), patch.object(s.time, "sleep") as sleep, patch.object(s.time, "time", side_effect=AssertionError("Wall clock used")):
            target = datetime.fromtimestamp(1792830000.5, timezone.utc)
            s.single_request(TOKEN, s.CONFIRMATION, target, directory=self.directory)
        self.assertEqual(sleep.call_count, 2)
        post.assert_called_once()

    @patch.object(s, "_post_once")
    def test_late_wake_does_not_send(self, post):
        with patch.object(s, "LIVE_REQUEST_ENABLED", True), patch.object(s, "check_account", return_value="eligible"), patch.object(s, "sample_clock", return_value=p.ClockSample(1792830000, 100, 0, .05)), patch.object(s.time, "monotonic", side_effect=[100, 200]), patch.object(s.time, "sleep"), self.assertRaises(p.CheckError):
            s.single_request(TOKEN, s.CONFIRMATION, datetime.fromtimestamp(1792830001, timezone.utc), directory=self.directory)
        post.assert_not_called()

    @patch.object(s.http.client, "HTTPSConnection")
    def test_one_post_and_fixed_format(self, factory):
        conn = factory.return_value
        conn.getresponse.return_value.status = 200
        conn.getresponse.return_value.read.return_value = b'{"code":0,"data":{"apply_result":1}}'
        self.assertEqual(self.run_attempt(), "approval_reported_unverified")
        conn.request.assert_called_once()
        self.assertEqual(conn.request.call_args.args, ("POST", s.APPLY_PATH))
        self.assertEqual(conn.request.call_args.kwargs["body"], b'{"is_retry":true}')
        headers = conn.request.call_args.kwargs["headers"]
        self.assertEqual(int(headers["Content-Length"]), len(s.APPLY_BODY))
        self.assertEqual(factory.call_args.args, (s.APPLY_HOST,))
        self.assertTrue(factory.call_args.kwargs["context"].check_hostname)
        conn.close.assert_called_once()

    @patch.object(s.http.client, "HTTPSConnection")
    def test_timeout_is_unknown_and_never_retried(self, factory):
        factory.return_value.request.side_effect = TimeoutError(TOKEN)
        self.assertEqual(self.run_attempt(), "outcome_unknown")
        factory.return_value.request.assert_called_once()
        with self.assertRaises(p.CheckError):
            self.run_attempt()
        factory.return_value.request.assert_called_once()

    def test_response_mapping(self):
        for status, body, expected in ((302, b"", "outcome_unknown"), (429, b"", "rate_limited"), (401, b"", "token_rejected"), (500, b"", "outcome_unknown"), (200, b"broken", "outcome_unknown"), (200, b"[]", "outcome_unknown"), (200, b'{"code":100003}', "outcome_unknown"), (200, b'{"code":false}', "outcome_unknown"), (200, b"x" * 65537, "outcome_unknown")):
            self.assertEqual(s.response_status(status, body), expected)
        for value, expected in ((1, "approval_reported_unverified"), (3, "quota_reported_full"), (4, "block_reported"), (True, "outcome_unknown"), (99, "outcome_unknown")):
            self.assertEqual(s.response_status(200, json.dumps({"code": 0, "data": {"apply_result": value}})), expected)

    def test_old_entry_points_are_inert(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("AutoStart.py", "AutoJobs.py", "Script.py", "GetTokens.py", "GetTokens for Gnome on Linux by Jenna-66.py"):
            spec = importlib.util.spec_from_file_location("old_entry", root / name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 2)


if __name__ == "__main__":
    unittest.main()
