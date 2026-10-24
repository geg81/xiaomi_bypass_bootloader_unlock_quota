# Work plan

## Open work

- Verify the first-request body and required fields against the current official client or official documentation.
- Keep live submission disabled until that contract review is complete.
- Review attempt-state recovery separately before permitting another application.

## Completion summary

- Disabled all old application launch and token helper entry points.
- Added guarded single-request mode, with no automatic retry or redirect.
- Added a shared process lock and a permanent attempt record before POST.
- Added fresh eligibility and NTP checks, bounded monotonic waiting, and fixed result labels.
- All 33 offline tests passed. No live request was sent for this milestone.
- The user reported a successful first-milestone dry run. Submission remains unverified.
- Source evidence and remaining contract limits are in doc/request-contract.md.

