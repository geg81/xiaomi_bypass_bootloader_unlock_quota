"""Test the preflight without live credentials or network access."""
import contextlib
from datetime import datetime, timezone
import importlib
import io
import json
import unittest
from unittest.mock import patch
import preflight as p

TOKEN = "test_only_token_123456789"


class PreflightTests(unittest.TestCase):
    def test_token_validation(self):
        self.assertEqual(p.validate_token(TOKEN), TOKEN)
        for value in (None, "", "short", TOKEN + ";x=y", TOKEN + "\r\n", "Cookie: " + TOKEN, "x" * 4097, "é" * 20):
            with self.subTest(value=type(value)), self.assertRaises(p.CheckError):
                p.validate_token(value)

    def test_account_states(self):
        for button, expected in ((1, "eligible"), (2, "blocked"), (3, "account_too_new"), (4, "unknown"), (True, "unknown")):
            self.assertEqual(p.eligibility({"code": 0, "data": {"is_pass": 4, "button_state": button}}), expected)
        self.assertEqual(p.eligibility({"code": 100004}), "token_rejected")
        self.assertEqual(p.eligibility({"code": 0, "data": {"is_pass": 1}}), "already_approved")
        for value in (None, [], {}, {"code": False}, {"code": 4, "data": {"is_pass": 4, "button_state": 1}}, {"code": 0, "data": None}):
            self.assertEqual(p.eligibility(value), "unknown")

    @patch("preflight.http.client.HTTPSConnection")
    def test_one_get_and_close(self, factory):
        connection = factory.return_value
        response = connection.getresponse.return_value
        response.status = 200
        response.read.return_value = json.dumps({"code": 0, "data": {"is_pass": 4, "button_state": 1}}).encode()
        self.assertEqual(p.check_account(TOKEN), "eligible")
        connection.request.assert_called_once()
        args = connection.request.call_args.args
        self.assertEqual(args, ("GET", p.STATE_PATH))
        self.assertEqual(factory.call_args.args, (p.HOST,))
        connection.close.assert_called_once()

    @patch("preflight.http.client.HTTPSConnection")
    def test_response_failures_do_not_retry(self, factory):
        for status, body in ((302, b""), (429, b""), (500, b""), (200, b"invalid"), (200, b"x" * 65537)):
            factory.reset_mock()
            conn = factory.return_value
            conn.getresponse.return_value.status = status
            conn.getresponse.return_value.read.return_value = body
            with self.assertRaises(p.CheckError):
                p.check_account(TOKEN)
            conn.request.assert_called_once()
            conn.close.assert_called_once()

    def packet(self):
        t1 = 1792830000.0
        sent = p.encode_stamp(t1)
        packet = bytearray(48)
        packet[0:2] = bytes([0x24, 2])
        packet[24:32] = sent
        packet[32:40] = p.encode_stamp(t1 + 0.15)
        packet[40:48] = p.encode_stamp(t1 + 0.16)
        return packet, sent, t1

    def test_ntp_four_timestamp_offset(self):
        packet, sent, t1 = self.packet()
        result = p.parse_ntp(packet, sent, t1, t1 + 0.21, 100, 100.21)
        self.assertAlmostEqual(result.offset, 0.05, places=5)
        self.assertAlmostEqual(result.delay, 0.20, places=5)
        self.assertAlmostEqual(result.utc, t1 + 0.26, places=5)
        self.assertEqual(result.monotonic, 100.21)

    def test_bad_ntp_packets(self):
        packet, sent, t1 = self.packet()
        variants = [packet[:20]]
        for index, value in ((0, 0xE4), (0, 0x23), (0, 0x14), (1, 0), (1, 16), (24, 255)):
            changed = packet.copy()
            changed[index] = value
            variants.append(changed)
        changed = packet.copy()
        changed[40:48] = bytes(8)
        variants.append(changed)
        for value in variants:
            with self.assertRaises(p.CheckError):
                p.parse_ntp(value, sent, t1, t1 + 0.21, 100, 100.21)
        with self.assertRaises(p.CheckError):
            p.parse_ntp(packet, sent, t1, t1 + 1, 100, 100.21)

    def test_ntp_era(self):
        for stamp in (1792830000.25, 2400000000.25):
            self.assertAlmostEqual(p.decode_stamp(p.encode_stamp(stamp), stamp), stamp)

    @patch("preflight.socket.getaddrinfo", return_value=[(2, 2, 17, "", ("192.0.2.1", 123))])
    @patch("preflight.socket.socket")
    def test_one_ntp_packet(self, socket_factory, addresses):
        packet, sent, t1 = self.packet()
        client = socket_factory.return_value.__enter__.return_value
        client.recv.return_value = bytes(packet)
        with patch("preflight.time.time", side_effect=[t1, t1 + 0.21]), patch("preflight.time.monotonic", side_effect=[100, 100.21]):
            result = p.sample_clock()
        client.send.assert_called_once_with(bytes([0x23]) + bytes(39) + sent)
        client.recv.assert_called_once_with(512)
        client.connect.assert_called_once_with(("192.0.2.1", 123))
        self.assertAlmostEqual(result.offset, 0.05, places=5)
        socket_factory.return_value.__exit__.assert_called_once()

    @patch("preflight.http.client.HTTPSConnection")
    def test_rejected_token(self, factory):
        for status in (401, 403):
            factory.reset_mock()
            connection = factory.return_value
            connection.getresponse.return_value.status = status
            self.assertEqual(p.check_account(TOKEN), "token_rejected")
            connection.request.assert_called_once()
            connection.close.assert_called_once()

    def test_schedule_midnight_and_clock_change(self):
        utc = datetime(2026, 10, 24, 15, 59, 59, tzinfo=timezone.utc).timestamp()
        sample = p.ClockSample(utc, 100, 0, 0.1)
        with patch("preflight.time.time", side_effect=AssertionError("Wall clock used")):
            target, deadline = p.schedule(sample, 100.5)
        self.assertEqual(target.isoformat(), "2026-10-25T00:00:00+08:00")
        self.assertEqual(deadline, 101)
        target, deadline = p.schedule(sample, 101)
        self.assertEqual(target.isoformat(), "2026-10-26T00:00:00+08:00")
        self.assertEqual(deadline, 86501)
        for now in (99, 161):
            with self.assertRaises(p.CheckError):
                p.schedule(sample, now)

    @patch.dict("os.environ", {"XIAOMI_SERVICE_TOKEN": TOKEN})
    @patch("preflight.sample_clock")
    @patch("preflight.check_account")
    def test_blocked_account_stops(self, account, clock):
        for state in ("blocked", "unknown", "account_too_new", "token_rejected", "already_approved"):
            account.return_value = state
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(p.main(["--dry-run"]), 2)
        clock.assert_not_called()

    @patch.dict("os.environ", {"XIAOMI_SERVICE_TOKEN": TOKEN})
    @patch("preflight.time.monotonic", return_value=100)
    @patch("preflight.sample_clock", return_value=p.ClockSample(1792830000, 100, 0.1, 0.2))
    @patch("preflight.check_account", return_value="eligible")
    def test_modes_do_not_wait_or_log_token(self, account, clock, monotonic):
        with patch("preflight.time.sleep", side_effect=AssertionError("Wait used")):
            for mode in ("--preflight", "--dry-run"):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(p.main([mode]), 0)
                self.assertNotIn(TOKEN, output.getvalue())
                self.assertIn("No application was submitted", output.getvalue())
                self.assertEqual("Dry-run target" in output.getvalue(), mode == "--dry-run")

    @patch("preflight.http.client.HTTPSConnection")
    def test_network_error_does_not_expose_token(self, factory):
        factory.return_value.request.side_effect = OSError(TOKEN)
        with self.assertRaises(p.CheckError) as result:
            p.check_account(TOKEN)
        self.assertNotIn(TOKEN, str(result.exception))

    def test_invalid_arguments_do_not_expose_token(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            p.main(["--token", TOKEN])
        self.assertNotIn(TOKEN, output.getvalue())

    def test_import_has_no_side_effects(self):
        with patch("socket.socket", side_effect=AssertionError("Network used")), patch("builtins.input", side_effect=AssertionError("Input used")):
            import NScript
            importlib.reload(NScript)


if __name__ == "__main__":
    unittest.main()
