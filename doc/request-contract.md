# Request contract review: 2026-10-24

## Result

The method, host, path, and inherited body agree across the inspected source
implementations. This is source-level evidence. It is not an official Xiaomi
contract and does not prove that the service accepts a first request today.
Live submission remains disabled in submission.py. There is no command option
or environment variable that bypasses this restriction.

| Item | Source evidence | Status |
| --- | --- | --- |
| Method | POST | Agrees across inspected sources |
| Host | sgp-api.buy.mi.com | Agrees across inspected sources |
| Path | /bbs/api/global/apply/bl-auth | Agrees across inspected sources |
| JSON body | {"is_retry":true} | Inherited; first-request meaning is not verified |
| Token | new_bbs_serviceToken cookie | Inherited; user reported a successful status GET |
| Content type | application/json; charset=utf-8 | Inherited |
| App version and device ID | Cookie fields from NScript.py | Required status is not verified |
| User agent | okhttp/4.12.0 | Inherited; required status is not verified |
| Response | code and data.apply_result | Inherited; approval is not confirmed |

The is_retry field is server data. It does not enable a client retry. Do not
change it to false without evidence. Do not use the request endpoint to test
which value works. A request can change account state.

## Sources

- Local upstream NScript.py and Script.py at commit
  39b6c65764a3a5cbe05974a6aa1f82584bec26df.
- [ednoct/micom source](https://github.com/ednoct/micom/blob/main/micomtool.py),
  inspected on 2026-10-24: apply_request uses the same endpoint and JSON body.
- [pwnj/auto-hyperos-unlocker source](https://github.com/pwnj/auto-hyperos-unlocker/blob/main/hyperosunlocker.py),
  inspected on 2026-10-24: the transport uses the same endpoint, body, and app
  cookie fields. This source can share ancestry with the original script.

A focused search did not locate an official Xiaomi specification for this
endpoint. Agreement between community programs is not independent proof of
the required fields or their current meaning.

## Required before live enablement

Obtain official request documentation or a redacted request specification from
the current official client. It must show method, host, path, field names,
non-secret body values, and response meanings. Do not collect passwords,
Cookie values, authorization headers, or a full HAR file. Do not send an
application only to collect this evidence. Review the evidence, update the
contract and fixtures, then review a separate change to enable live use.

## Single-request controls

The disabled live mode is --submit-once. It requires the exact confirmation
SEND ONE REQUEST before the account check. An optional --target value must be
an ISO time with a UTC offset within the next 60 seconds. There is no automatic
midnight wait and no early-send offset. Account eligibility and NTP time are
checked once before a short monotonic wait. A missed target stops the run.

All working directories and repository copies for the same operating-system
user share ~/.xiaomi-unlock. An exclusive active.lock directory stops a second
process. A crash can leave that lock in place; the program does not clear it.
Before any POST, an exclusive attempt.json file is written, flushed, and
synchronized to disk. Its fixed outcome_unknown state remains after every
result. It contains only a schema version, state, and UTC creation time.
It has no token, account identifier, Cookie header, password, or response body.

A new run stops when the record exists, including after a token change or a
new day. There is no reset command or automatic record expiry. A timeout,
interruption, redirect, server error, or malformed response never causes a
second POST. No automatic follow-up GET is made after the POST.

This protection applies to one operating-system user and its local state
directory. It cannot stop another computer, another user, manual state-file
removal, or a separate client. It is not server-side idempotency. Storage or
power failures can exceed the guarantees of flush and fsync. Use local storage.
Do not remove a lock or record to repeat an application with an unknown result.
Check the account manually first and review recovery separately.

## Verification

33 offline tests passed on Python 3.14. Tests use synthetic tokens, mocked
HTTP and NTP calls, a temporary state directory, and one real child process
for lock contention. Tests block socket creation in the submission test suite.
No live Xiaomi request or NTP check was made for this milestone.

The user reported one successful milestone-one dry run on 2026-10-24:
account eligible, NTP offset -2.979255 s, round-trip delay 0.050039 s.
This is user-reported evidence for the status and time checks, not a live
submission test or proof of quota availability.

