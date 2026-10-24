"""Control one application attempt. Live use is disabled pending contract review."""
from contextlib import contextmanager
from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import secrets
import ssl
import time

from preflight import CheckError, check_account, sample_clock, validate_token

# Do not enable this until the request contract has been verified.
LIVE_REQUEST_ENABLED = False
APPLY_HOST = "sgp-api.buy.mi.com"
APPLY_PATH = "/bbs/api/global/apply/bl-auth"
# This body is inherited evidence, not a verified first-request contract.
APPLY_BODY = b'{"is_retry":true}'
STATE_DIR = Path.home() / ".xiaomi-unlock"
CONFIRMATION = "SEND ONE REQUEST"


@contextmanager
def attempt_lock(directory):
    """Stop if another process or an unresolved attempt exists."""
    lock = directory / "active.lock"
    owned = False
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock.mkdir(mode=0o700)
        owned = True
        if (directory / "attempt.json").exists():
            raise CheckError("An attempt record exists. Check the account manually. Do not submit again.")
        yield
    except OSError:
        raise CheckError("The attempt state is locked or unavailable. No new request is permitted.") from None
    finally:
        if owned:
            # A failed cleanup leaves a lock in place and prevents another run.
            try:
                lock.rmdir()
            except OSError:
                pass


def record_attempt(directory):
    """Make a permanent record before the network call."""
    record = {"version": 1, "state": "outcome_unknown", "created_utc": datetime.now(timezone.utc).isoformat()}
    try:
        # Exclusive creation prevents a second attempt after a process race.
        with (directory / "attempt.json").open("x", encoding="utf-8") as stream:
            json.dump(record, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise CheckError("The attempt record could not be saved. No request was sent.") from None


def response_status(status, body):
    if status == 429:
        return "rate_limited"
    if status in (401, 403):
        return "token_rejected"
    if status != 200 or len(body) > 65536:
        return "outcome_unknown"
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):
        return "outcome_unknown"
    if not isinstance(payload, dict) or type(payload.get("code")) is not int:
        return "outcome_unknown"
    if payload["code"] == 100004:
        return "token_rejected"
    if payload["code"] != 0:
        return "outcome_unknown"
    data = payload.get("data")
    if not isinstance(data, dict) or type(data.get("apply_result")) is not int:
        return "outcome_unknown"
    return {1: "approval_reported_unverified", 3: "quota_reported_full", 4: "block_reported"}.get(data["apply_result"], "outcome_unknown")


def _post_once(token):
    """Send one POST. Never follow a redirect or retry a failure."""
    if not LIVE_REQUEST_ENABLED:
        raise CheckError("Live submission is disabled pending request contract review.")
    connection = None
    try:
        connection = http.client.HTTPSConnection(APPLY_HOST, timeout=10, context=ssl.create_default_context())
        connection.request("POST", APPLY_PATH, body=APPLY_BODY, headers={
            "Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={secrets.token_hex(20).upper()};",
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(APPLY_BODY)),
            "Accept": "application/json", "Accept-Encoding": "identity",
            "User-Agent": "okhttp/4.12.0", "Connection": "close",
        })
        response = connection.getresponse()
        return response_status(response.status, response.read(65537))
    except (OSError, http.client.HTTPException, ValueError):
        return "outcome_unknown"
    finally:
        if connection is not None:
            connection.close()


def single_request(token, confirmation, target=None, server="time.google.com", *, directory=None):
    """Check the account and time, then permit at most one attempt."""
    if not LIVE_REQUEST_ENABLED:
        raise CheckError("Live submission is disabled pending request contract review.")
    if confirmation != CONFIRMATION:
        raise CheckError("Confirmation did not match. No request was sent.")
    token = validate_token(token)
    directory = STATE_DIR if directory is None else directory
    with attempt_lock(directory):
        if check_account(token) != "eligible":
            raise CheckError("The account is not eligible. No request was sent.")
        sample = sample_clock(server)
        now = time.monotonic()
        age = now - sample.monotonic
        if not 0 <= age <= 5:
            raise CheckError("The time sample is stale. No request was sent.")
        deadline = now
        if target is not None:
            if target.tzinfo is None or target.utcoffset() is None:
                raise CheckError("The target needs a UTC offset. No request was sent.")
            deadline = sample.monotonic + target.timestamp() - sample.utc
            if not 0 <= deadline - now <= 60:
                raise CheckError("The target must be within the next 60 seconds. No request was sent.")
        while now < deadline:
            time.sleep(min(0.25, deadline - now))
            now = time.monotonic()
        if now - deadline > 2 or now - sample.monotonic > 65:
            raise CheckError("The target was missed. No request was sent.")
        record_attempt(directory)
        # From this point, all failures have an unknown outcome. Keep the record.
        try:
            if time.monotonic() - deadline > 2:
                return "outcome_unknown"
            return _post_once(token)
        except BaseException:
            # Do not claim that nothing was sent after an interrupted call.
            return "outcome_unknown"
