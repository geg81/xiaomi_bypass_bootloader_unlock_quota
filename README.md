# Preflight and single-request controls

Use Python 3.10 or later. Only the Python standard library is required.

```powershell
python NScript.py --preflight
python NScript.py --dry-run
python -m preflight --dry-run
```

Enter only the new_bbs_serviceToken value at the hidden prompt. Do not enter a
password or a complete Cookie header. Never put a token in command arguments,
source files, logs, issues, or chat. An existing process environment variable
named XIAOMI_SERVICE_TOKEN can supply the token. The tool does not read or
write account.txt or token.txt. It stops if hidden input is unavailable.

Preflight and dry run make at most one account status GET and one NTP request.
Dry run is not offline. It sends the token only to the fixed Xiaomi status
host through verified TLS. It does not submit, follow redirects, use proxy
environment settings, retry, or wait for midnight. A blocked, new, approved,
rejected, or unknown account state stops the checks.

Dry run shows the next midnight at UTC+08:00 and its monotonic deadline.
This is a schedule example, not proof of a quota opening. NTP uses four
timestamps. NTP is not authenticated and one sample gives no precision
guarantee. The tool does not change the system clock.

## Single-request milestone

--submit-once is implemented but live use is disabled pending request contract
review. The command stops before token input or network access. There is no
command-line bypass. See [the contract review](doc/request-contract.md).

The tested path has one POST, no retries, a process lock, and a permanent
attempt record saved before the request. A timeout or interruption is an
unknown outcome. It must not cause another request. After future enablement,
the path requires explicit confirmation and fresh account and time checks.
An optional --target ISO time must include a UTC offset and be within the next
60 seconds. It uses a short monotonic wait with no early-send offset.

The state directory is ~/.xiaomi-unlock, shared by repository copies for the
same operating-system user. There is no automatic reset, expiry, or retry.
The record contains no credentials or account data. Separate computers and
users are not covered by this local protection.

The old AutoStart.bat, AutoStart.py, AutoJobs.py, Script.py, and both GetTokens
entry points are disabled. They only print a fixed message and exit. Their
original source remains in Git history. Ping.bat does not submit applications.

## Tests and result codes

```powershell
python -m unittest discover -s tests -v
```

Tests are offline. No live application was sent during development.
Exit code 0 means that preflight passed. Exit code 2 means that a check or
option failed before submission. Exit code 3 means an application attempt
needs manual review; it does not prove approval. Exit code 130 means that the
user stopped before an application attempt. An interruption after the attempt
record is saved is treated as an unknown outcome, with the record retained.

See [the code map](doc/code-map.md) and [the work plan](planning.md).
The [first review](doc/security-review.md) records the original findings.

Source: [matedon/xiaomi_bypass_bootloader_unlock_quota](https://github.com/matedon/xiaomi_bypass_bootloader_unlock_quota).
Original helper credits include byBestix and Jenna-66. Git history retains the
original source and credits.
