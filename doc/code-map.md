# Code map

| Part | Main file and symbols | Tests |
| --- | --- | --- |
| Command entry | NScript.py; preflight.py: main, SafeParser | Modes, import, argument errors |
| Token and account | preflight.py: validate_token, eligibility, check_account | Input, states, one GET, failures |
| Time | preflight.py: sample_clock, parse_ntp, schedule | NTP offset, invalid packets, era, midnight |
| Offline tests | tests/test_preflight.py | Python unittest discovery |
| Original helpers | AutoJobs.py, AutoStart.py, Script.py, GetTokens.py | Not accepted for this milestone |
