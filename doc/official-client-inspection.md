# Official website inspection: 2026-10-24

## Result

The inspected website build did not expose the application request builder.
This inspection does not verify the inherited POST body. Live submission
remains disabled. APK inspection is pending because no official package file
was obtained.

## Method and scope

The public HTML was downloaded from https://c.mi.com/global/ with Python's
standard HTTP client. No browser session, account token, Cookie header,
password, or account storage was used. Only public static files were fetched.
No account API or application API was called. No downloaded code was executed.

The HTML links five Xiaomi-hosted JavaScript bundles. The main bundle lists
163 additional JavaScript chunks. All 168 files were downloaded successfully,
for a total of 13,355,064 bytes. The homepage HTML was 2,721 bytes.
Third-party utility scripts, images, and CSS were outside the source search.

Literal searches, without case sensitivity, found zero matches for bl-auth,
bl-switch, is_retry, and .apk in these 168 JavaScript files. The initial files
were also checked for bootloader text. Matches in the additional chunks led
to the instructions component described below.

This is a bounded static inspection. It does not prove that an application
function is absent from every Xiaomi site, another build, an app webview,
encoded strings, or code fetched from a different source at runtime.

## Located bootloader page

File: 132.chunk.1655eb33.js, 2,888 bytes.
Module: 2129. Component class: m-bl-lock.

The component renders instructions, eligibility text, and a tutorial link.
It does not contain a form submission handler or an application API call.
It links to https://new.c.mi.com/global/post/710306. Its instruction text
still refers to applications before the end of 2024. Do not treat this text
as evidence of current quota policy or timing.

Source:
https://cdn.alsgp0.fds.api.mi-img.com/micomm/static/js/132.chunk.1655eb33.js

## Official APK source check

The common bundle defines appDownloadUrl values that point to Google Play,
including https://play.google.com/store/apps/details?id=com.mi.global.bbs.
The public Play listing identifies Xiaomi Community, publisher Xiaomi, and
package com.mi.global.bbs. It did not expose a direct APK link in the retrieved
public page. No Play account was accessed and no installation was requested.

The direct GetApps listing candidate
https://global.app.mi.com/details?id=com.mi.global.bbs
returned HTTP 404 through the independent HTTP client. Search results also
included third-party APK mirrors. No mirror package was downloaded or treated
as an authenticated official APK.

No APK was present in this workspace. The adb command was not available on
PATH. No phone, installed app data, or wider personal folders were inspected.
Consequently, there is no APK hash, signing-certificate result, manifest
version, or DEX inspection result to report.

## Evidence retained

- doc/evidence/website-manifest-2026-10-24.json contains each public JavaScript
  URL, filename, byte count, and SHA-256 hash, plus the homepage hash.
- inspection/ contains the downloaded HTML and original JavaScript files.
  This local folder is excluded from Git. No third-party code is published.
- tools/check_website_evidence.py checks the saved file hashes and repeats the
  literal searches offline. It does not read tokens or access the network.

## Next required input

Provide only the APK package from the official Xiaomi Community installation
or an official public APK download link. If the installation uses split APKs,
provide the base package and its splits. Do not provide app-data backups,
account files, cookies, tokens, or network captures. Record the installation
source and app version. Package provenance must be checked before treating
its code as official evidence.

The next inspection can check the signing certificate, package metadata,
request builder, is_retry branch conditions, and response handler offline.
It will not install or run the app and will not send an application.
