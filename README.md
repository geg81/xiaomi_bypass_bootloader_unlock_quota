# Preflight checks

This first milestone replaces `NScript.py` with a preflight entry point.
It cannot send an unlock application. It does not install packages.
Use Python 3.10 or later. Only the Python standard library is required.

Run one of these commands:

```powershell
python NScript.py --preflight
python NScript.py --dry-run
python -m preflight --dry-run
```

Enter only the `new_bbs_serviceToken` value at the hidden prompt.
Do not enter a password or a full Cookie header. Do not put a token in a
command argument, source file, log, issue, or chat. An existing process
environment variable named `XIAOMI_SERVICE_TOKEN` can supply the token.
The tool does not read or write account.txt or token.txt.
If hidden input is not available, the tool stops.

Both modes make at most one account status GET request and one NTP request.
Dry run is not an offline mode. It sends the token only to the fixed Xiaomi
status host through verified TLS. It does not follow redirects, use environment
proxy settings, retry, wait for midnight, or send an application.

A successful account check must return an eligible state before the NTP check.
Blocked, new, approved, rejected, and unknown states stop the checks.
Exit code 0 means that the checks passed. Exit code 2 means that a check or
command option failed. Exit code 130 means that the user stopped the checks.

Dry run shows the next midnight at UTC+08:00 and its monotonic deadline.
This is a schedule example. It does not prove that Xiaomi opens a quota then.
The NTP sample uses all four timestamps. The schedule uses monotonic time.
The tool rejects a clock step, an old sample, or an invalid NTP response.
It does not change the system clock. NTP is not authenticated. One sample
cannot provide a precision guarantee or detect all false time responses.

The eligibility fields come from the original repository. They are not a
verified public Xiaomi API contract. Unknown responses stop the checks.
Token syntax validation does not prove that a token is valid. The status
request checks whether the service accepts it.

Run the offline tests:

```powershell
python -m unittest discover -s tests -v
```

Do not use `AutoJobs.py`, `AutoStart.py`, `AutoStart.bat`, `Script.py`, or the
`GetTokens` helpers for this milestone. These original files remain for later
review. They can store credentials, print token prefixes, launch multiple
processes, or send applications. The preflight tool does not import them.

See [the code map](doc/code-map.md), [the review](doc/security-review.md),
and [the work plan](planning.md).

Source: [matedon/xiaomi_bypass_bootloader_unlock_quota](https://github.com/matedon/xiaomi_bypass_bootloader_unlock_quota). Original helper credits include byBestix and Jenna-66. The original files and Git history retain their source credits.
