# Code map

| Part | Main file and symbols | Tests |
| --- | --- | --- |
| Command entry | NScript.py; preflight.py: main, SafeParser | Modes, import, argument errors, live gate |
| Token and account | preflight.py: validate_token, eligibility, check_account | Input, states, one GET, failures |
| Time | preflight.py: sample_clock, parse_ntp, schedule | NTP offset, invalid packets, era, midnight |
| Single attempt | submission.py: single_request, _post_once, response_status | One POST, fixed format, timeout, response mapping |
| Duplicate protection | submission.py: attempt_lock, record_attempt | Child process, restart, crash, disk failure |
| Offline tests | tests/test_preflight.py, tests/test_submission.py | Python unittest discovery |
| Disabled old entry points | AutoStart.bat, AutoStart.py, AutoJobs.py, Script.py, both GetTokens files | Inert import and exit |
| Request evidence | doc/request-contract.md | Source review; no live application |
