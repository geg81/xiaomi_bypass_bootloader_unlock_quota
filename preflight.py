"""Run account checks or select the guarded single-request mode."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import getpass
import http.client
import json
import math
import os
import re
import secrets
import socket
import ssl
import struct
import time
import warnings

HOST = "sgp-api.buy.mi.com"
STATE_PATH = "/bbs/api/global/user/bl-switch/state"
BEIJING = timezone(timedelta(hours=8))
NTP_EPOCH = 2208988800


class CheckError(Exception):
    """Report a fixed message that contains no secret data."""


def validate_token(value):
    # Accept one cookie value, not a complete Cookie header.
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_~.%+/=-]{16,4096}", value):
        raise CheckError("Token format is invalid.")
    return value


def eligibility(payload):
    if not isinstance(payload, dict) or type(payload.get("code")) is not int:
        return "unknown"
    if payload["code"] == 100004:
        return "token_rejected"
    if payload["code"] != 0 or not isinstance(payload.get("data"), dict):
        return "unknown"
    data = payload["data"]
    state, button = data.get("is_pass"), data.get("button_state")
    if type(state) is not int:
        return "unknown"
    if state == 1:
        return "already_approved"
    if state == 4 and type(button) is int:
        return {1: "eligible", 2: "blocked", 3: "account_too_new"}.get(button, "unknown")
    return "unknown"


def check_account(token):
    token = validate_token(token)
    # Direct TLS keeps credentials out of proxy settings and redirect targets.
    connection = http.client.HTTPSConnection(HOST, timeout=10, context=ssl.create_default_context())
    try:
        connection.request("GET", STATE_PATH, headers={
            "Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={secrets.token_hex(20).upper()};",
            "Accept": "application/json", "Accept-Encoding": "identity",
        })
        response = connection.getresponse()
        if response.status in (401, 403):
            return "token_rejected"
        if response.status == 429:
            raise CheckError("The service rate limit is active. No retry was made.")
        if response.status != 200:
            raise CheckError("The account check failed. No retry was made.")
        body = response.read(65537)
        if len(body) > 65536:
            raise CheckError("The account response is too large.")
        return eligibility(json.loads(body))
    except (OSError, http.client.HTTPException, ValueError, RecursionError):
        raise CheckError("The account response could not be read. No retry was made.") from None
    finally:
        connection.close()


@dataclass(frozen=True)
class ClockSample:
    utc: float
    monotonic: float
    offset: float
    delay: float


def encode_stamp(unix):
    value = unix + NTP_EPOCH
    seconds = math.floor(value)
    return struct.pack("!II", seconds % 2**32, int((value - seconds) * 2**32))


def decode_stamp(raw, near):
    seconds, fraction = struct.unpack("!II", raw)
    base = seconds + fraction / 2**32 - NTP_EPOCH
    return base + round((near - base) / 2**32) * 2**32


def parse_ntp(packet, sent, t1, t4, m1, m4):
    if len(packet) < 48:
        raise CheckError("The NTP response is incomplete.")
    flags, stratum = packet[0], packet[1]
    if flags >> 6 == 3 or ((flags >> 3) & 7) not in (3, 4) or (flags & 7) != 4 or not 1 <= stratum <= 15:
        raise CheckError("The NTP server is not ready.")
    if packet[24:32] != sent or packet[32:40] == bytes(8) or packet[40:48] == bytes(8):
        raise CheckError("The NTP timestamps are invalid.")
    elapsed = m4 - m1
    if elapsed < 0 or abs((t4 - t1) - elapsed) > 0.05:
        raise CheckError("The system clock changed during the NTP check.")
    t2 = decode_stamp(packet[32:40], t1)
    t3 = decode_stamp(packet[40:48], t1)
    offset = ((t2 - t1) + (t3 - t4)) / 2
    delay = (t4 - t1) - (t3 - t2)
    if t3 < t2 or not -0.001 <= delay <= 2 or abs(offset) > 300:
        raise CheckError("The NTP sample is outside the permitted limits.")
    return ClockSample(t4 + offset, m4, offset, max(0, delay))


def sample_clock(server="time.google.com"):
    try:
        # Use one address and one packet. A connected socket checks the peer.
        family, kind, protocol, _, address = socket.getaddrinfo(server, 123, type=socket.SOCK_DGRAM)[0]
        with socket.socket(family, kind, protocol) as client:
            client.settimeout(3)
            client.connect(address)
            m1 = time.monotonic()
            t1 = time.time()
            sent = encode_stamp(t1)
            client.send(bytes([0x23]) + bytes(39) + sent)
            packet = client.recv(512)
            m4 = time.monotonic()
            t4 = time.time()
        return parse_ntp(packet, sent, t1, t4, m1, m4)
    except (OSError, IndexError, UnicodeError):
        raise CheckError("The NTP check failed. No retry was made.") from None


def schedule(sample, now_mono):
    age = now_mono - sample.monotonic
    if not 0 <= age <= 60:
        raise CheckError("The clock sample is too old or invalid.")
    now = datetime.fromtimestamp(sample.utc + age, BEIJING)
    target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    deadline = sample.monotonic + target.timestamp() - sample.utc
    return target, deadline


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # Argument errors can contain a secret entered in the wrong field.
        self.print_usage()
        self.exit(2, "Invalid command options. Use --help.\n")


def main(argv=None):
    parser = SafeParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="Check the account and clock, then exit.")
    mode.add_argument("--dry-run", action="store_true", help="Also show the schedule. Do not wait or submit.")
    mode.add_argument("--submit-once", action="store_true", help="Select one request. Live use is disabled pending contract review.")
    parser.add_argument("--target", help="Optional ISO time with UTC offset, at most 60 seconds ahead.")
    parser.add_argument("--ntp-server", default="time.google.com", help="Use this NTP server for one sample.")
    args = parser.parse_args(argv)
    try:
        target = None
        if args.target:
            if not args.submit_once:
                raise CheckError("The target option requires single-request mode.")
            try:
                target = datetime.fromisoformat(args.target)
                if target.utcoffset() is None:
                    raise ValueError()
            except ValueError:
                raise CheckError("The target must be an ISO time with a UTC offset.") from None
        if args.submit_once:
            import submission
            if not submission.LIVE_REQUEST_ENABLED:
                raise CheckError("Live submission is disabled pending request contract review.")
        token = os.environ.get("XIAOMI_SERVICE_TOKEN")
        if token is None:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                token = getpass.getpass("Service token (input hidden): ")
        token = validate_token(token)
        if args.submit_once:
            confirmation = input("Type SEND ONE REQUEST to permit one attempt: ")
            result = submission.single_request(token, confirmation, target, args.ntp_server)
            print(f"Application result: {result}.")
            print("The attempt record remains. Check the account manually before any further action.")
            return 3
        status = check_account(token)
        print(f"Account status: {status}.")
        if status != "eligible":
            return 2
        sample = sample_clock(args.ntp_server)
        print(f"NTP offset: {sample.offset:.6f} s. Round-trip delay: {sample.delay:.6f} s.")
        if args.dry_run:
            target, deadline = schedule(sample, time.monotonic())
            print(f"Dry-run target: {target.isoformat()}.")
            print(f"Monotonic deadline: {deadline:.6f} s.")
        print("Checks complete. No application was submitted.")
        return 0
    except CheckError as error:
        print(str(error))
        print("Preflight failed. No application was submitted.")
        return 2
    except (EOFError, getpass.GetPassWarning):
        print("Secure token input is not available. No application was submitted.")
        return 2
    except KeyboardInterrupt:
        print("Checks stopped. No application was submitted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
