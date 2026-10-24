# Work plan

## Open work

- Obtain an official Xiaomi Community APK, then inspect the request builder offline. Public website inspection did not resolve the request format.
- Keep live submission disabled until that contract review is complete.
- Review attempt-state recovery separately before permitting another application.

## Completion summary

- Inspected all 168 JavaScript files listed by the official homepage. Found instructions but no application request builder. Saved source hashes and a local evidence check.
- Checked official APK distribution links. No package was obtained. No browser session, token, or application endpoint was accessed.
- Disabled all old application launch and token helper entry points.
- Added guarded single-request mode, with no automatic retry or redirect.
- Added a shared process lock and a permanent attempt record before POST.
- Added fresh eligibility and NTP checks, bounded monotonic waiting, and fixed result labels.
- All 33 offline tests passed. No live request was sent for this milestone.
- The user reported a successful first-milestone dry run. Submission remains unverified.
- Source evidence and remaining contract limits are in doc/request-contract.md.

