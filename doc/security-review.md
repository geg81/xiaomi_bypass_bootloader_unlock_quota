# Security review: 2026-10-24

Source: matedon/xiaomi_bypass_bootloader_unlock_quota.
Inspected commit: 39b6c65764a3a5cbe05974a6aa1f82584bec26df.

The original NScript.py installs packages at import, reads tokens from a file,
permits blocked accounts to continue, uses wall time for elapsed time, prints
raw responses and exceptions, and sends POST requests in an unbounded loop.
The replacement removes these operations from the supported entry point.

The new account transport has a fixed host and path. It uses certificate
verification, one GET request, a 10-second socket timeout, a 64 KiB body limit,
and no redirects or retries. Socket timeouts are not a total runtime limit.
DNS resolution uses the operating system and can take longer than the socket
timeout. Only fixed status names and fixed error messages are printed.
No account response, identifier, token, Cookie header, or password is logged.
The tool creates no log files. Process memory can still contain the token.

NTP uses one UDP request with a 3-second socket timeout. It checks the peer,
mode, version, leap state, stratum, origin timestamp, receive timestamp, and
transmit timestamp. It rejects a wall-clock step greater than 50 ms, a network
delay greater than 2 s, or an absolute offset greater than 300 s. The sample
must be at most 60 s old when the schedule is calculated. The NTP era is
resolved near the local clock. The clock must therefore be approximately
correct. The response is not authenticated. This is a diagnostic SNTP sample,
not a full NTP clock service or a precision guarantee.

Reference: [RFC 5905, section 8](https://www.rfc-editor.org/rfc/rfc5905.html#section-8).
No third-party PDF was supplied or copied into this project.

The account response mapping is inherited from the source script. It has not
been checked with a live account. No credentials were used in development.
Tests use synthetic data and mocked network calls. Live account access and
live NTP access remain unverified.

Original helpers remain outside the supported path. AutoJobs.py prints token
prefixes and starts repeated token refresh and multiple script processes.
Script.py still contains application code. Do not run these files as part of
preflight. A later milestone must review or retire them before wider use.

No license file was present in the inspected source tree. This review does
not establish permission for wider redistribution.
