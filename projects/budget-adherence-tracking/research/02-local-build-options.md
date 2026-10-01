# Research pass 2: budget-adherence-tracking (local platform questions A–G)

Date of research: 2026-09-24. I checked each claim against official documentation or repositories where I could reach them. This pass is focused, not exhaustive: 29 tool calls. It does not recommend an architecture.

## Research objective
Check the platform facts that pass 1 left open for a $0 budget app that runs only on the user's Mac (Australia), so the architect can reason about data leaving the machine, storage, packaging, and setup effort for a non-specialist.

## Questions investigated
- A. Which network address common local servers listen on by default.
- B. Storage: SQLite in Python, SQLCipher, FileVault defaults.
- C. Packaging: Electron and Tauri requirements, Gatekeeper, Apple Developer Program fee.
- D. A browser-only app saving to a real file (File System Access API).
- E. Licences of free chart libraries, and whether they can be bundled locally.
- F. Free spreadsheet options.
- G. Whether Python and Node come with macOS, and how to install them.

---

## Key findings

### A. Default listening address

| Server | Default | Classification | Source |
|---|---|---|---|
| Python `http.server` (`python -m http.server`) | **All interfaces.** Docs: "By default, the server binds itself to all interfaces." The docs also say it is "not recommended for production" and only has basic security checks. | VERIFIED | https://docs.python.org/3/library/http.server.html |
| Flask `app.run()` / dev server | **127.0.0.1.** Docs: "Defaults to '127.0.0.1' or the host in the SERVER_NAME config variable if present." Setting `'0.0.0.0'` makes it visible to other machines. | VERIFIED | https://flask.palletsprojects.com/en/stable/api/ |
| Uvicorn (the usual server for FastAPI) | **127.0.0.1.** `--host` "Default: '127.0.0.1'." | VERIFIED (read from the docs source on GitHub; uvicorn.org did not resolve during this session) | https://github.com/encode/uvicorn/blob/master/docs/settings.md |
| Node `net`/`http` `server.listen()` with no host | **All interfaces.** Docs: "If host is omitted, the server will accept connections on the unspecified IPv6 address (::) when IPv6 is available, or the unspecified IPv4 address (0.0.0.0) otherwise." Listening on `::` may also listen on 0.0.0.0. | VERIFIED | https://nodejs.org/api/net.html |
| Vite dev server `server.host` | **'localhost'.** Setting `0.0.0.0` or `true` listens "on all addresses, including LAN and public addresses." | VERIFIED | https://vite.dev/config/server-options |

In practice, two of the five listen on every network interface by default: Python `http.server` and a bare Node `listen()`. Unless the host is set to 127.0.0.1, other devices on the same network (for example home or café Wi-Fi) could reach the app. Whether the macOS application firewall would block that depends on the user's firewall setting, which I did not research (UNKNOWN).

### B. On-disk storage

- **`sqlite3` is in Python's standard library, but officially an "optional module".** Docs: "If it is missing from your copy of CPython, look for documentation from your distributor." The docs also say macOS SQLite libraries are built without loadable-extension support. VERIFIED. https://docs.python.org/3/library/sqlite3.html
- That the python.org macOS installer and Apple's Command Line Tools Python both include a working `sqlite3`: LIKELY (widely assumed, not checked this pass).
- **SQLCipher Community Edition** is BSD-3-Clause and free. The official repo covers building from source (it needs a crypto provider such as OpenSSL) and does not mention prebuilt binaries or Python bindings. VERIFIED (licence). https://github.com/sqlcipher/sqlcipher
  - Installing it at $0 on a Mac without building from source (for example via Homebrew or third-party Python bindings): UNCERTAIN, not researched. It clearly adds setup complexity for a non-specialist.
- **Disk encryption on Apple silicon and T2 Macs happens automatically.** Apple: "If you have a Mac with Apple silicon or an Apple T2 Security Chip, your data is encrypted automatically. Turning on FileVault provides an extra layer of security…" VERIFIED. https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac
  - Apple's Platform Security guide says that if FileVault is not turned on during Setup Assistant, the volume is still encrypted, but its key is protected only by the hardware in the Secure Enclave, not by the login password. VERIFIED. https://support.apple.com/guide/security/volume-encryption-with-filevault-sec4c6dc1b6e/web
  - **Whether FileVault itself is on by default:** UNCERTAIN. Apple's docs say it can be turned on in Setup Assistant, and managed organisations can require it, but none of the pages I read says it is on by default for consumer setups. The user's actual FileVault status is UNKNOWN; it can be checked in System Settings > Privacy & Security > FileVault.

### C. Packaging and Gatekeeper

- **Electron:** MIT licence. Prebuilt binaries for "macOS (Ventura and up)", Intel and Apple Silicon. VERIFIED. https://github.com/electron/electron/blob/main/README.md
  - Building Electron itself from source needs macOS 12 or later, but normal app developers do not need to do that. VERIFIED. https://www.electronjs.org/docs/latest/development/build-instructions-macos
- **Tauri v2** on macOS needs Xcode ("Be sure to launch Xcode after installing"), Rust (via rustup) and Node.js LTS. Minimum is macOS Catalina (10.15). VERIFIED. https://v2.tauri.app/start/prerequisites/
  - That the full Xcode download is several GB and adds a Rust toolchain: LIKELY. That makes setup noticeably heavier for a non-specialist than Python or Node alone.
- **Gatekeeper and apps built on the user's own Mac:**
  - Apple's security guide describes Gatekeeper as running when a user downloads and opens an app. It also says "all software in macOS is checked for known malicious content the first time it's opened, regardless of how it arrived on the Mac." VERIFIED. https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web
  - An Apple support engineer wrote on Apple's developer forums in November 2020: "Gatekeeper usually only kicks in [if] the app is quarantined." Web browsers mark downloaded files with a quarantine flag (the `com.apple.quarantine` attribute); curl and scp do not. https://developer.apple.com/forums/thread/666452
  - Conclusion: an app built on the user's own Mac, which never gets that flag, will not show the Gatekeeper "unidentified developer" block. Classification: CORROBORATED, not VERIFIED. The source is an Apple engineer in a forum rather than formal documentation, it is from 2020, and it says "usually".
  - That Apple silicon requires at least ad-hoc code signing (a free signature with no certificate) and that standard toolchains apply it automatically: LIKELY, not verified this pass.
- **Apple Developer Program:** USD 99 per year, "in local currency where available". https://developer.apple.com/programs/enroll/ and https://developer.apple.com/support/compare-memberships/
  - Notarization (Apple's malware check for distributed apps) requires the paid membership. VERIFIED.
  - A free Apple Account can sign apps with Xcode as a "Personal Team". The page shows limits (for example, provisioning profiles expire after 7 days) that appear to apply to installing on registered devices.
  - The AUD price (reportedly A$149) is UNCERTAIN: only one search summary gave that figure, and Apple's pages show local price only during enrolment. It does not matter for a $0 local-only app, which does not need the program.

### D. Browser-only app saving to a real file (File System Access API)

- `showSaveFilePicker()` is marked "Limited availability", "Experimental", secure-context only, and requires a user action such as a click. VERIFIED. https://developer.mozilla.org/en-US/docs/Web/API/Window/showSaveFilePicker
- Browser support per caniuse (checked 2026-09-24): https://caniuse.com/native-filesystem-api
  - Chrome and Edge: supported since version 105. VERIFIED.
  - Safari on macOS: not supported in any version. VERIFIED.
  - Firefox: not supported; Mozilla's standards position calls the API "harmful". VERIFIED.
- So a browser app can write its data to a real file on disk only in Chrome or Edge. In Safari or Firefox, the fallback is browser storage (IndexedDB or similar), which pass 1 found can be evicted. The other fallback is manually exporting and importing a file with download and upload.
- Whether `http://localhost` counts as a secure context: LIKELY yes (standard browser behaviour), not re-checked this pass.
- Safari's support for the Origin Private File System (a private storage area inside the browser, not a user-visible file): not researched, UNKNOWN. It would not give the user a real file on disk anyway.

### E. Free chart libraries

| Library | Licence | Notes | Classification |
|---|---|---|---|
| Chart.js | MIT | "Chart.js is available under the MIT license"; v4 | VERIFIED. https://github.com/chartjs/Chart.js |
| Apache ECharts | Apache-2.0 | Published on npm | CORROBORATED. https://github.com/apache/echarts, https://www.npmjs.com/package/echarts |
| uPlot | MIT | "A small (~50 KB min), fast chart for time series… (MIT Licensed)" | VERIFIED. https://github.com/leeoniya/uPlot |
| Recharts | MIT | **Requires React**: `npm install recharts react-is` | VERIFIED. https://github.com/recharts/recharts |

- **Bundling locally, no CDN:** all four are published as npm packages, and their licences allow redistribution. Local bundling or copying the file into the app is therefore possible. Classification: LIKELY/CORROBORATED; this is inferred from npm distribution and permissive licences, and I did not read each library's install docs.
- Apache-2.0 and MIT require keeping the licence notice.

### F. Spreadsheet options

- **Apple Numbers:** free on the Mac App Store, no subscription needed to create or edit. Search summary of Apple sources: CORROBORATED. The Mac App Store page was not opened directly this pass. https://apps.apple.com/in/app/numbers/id409203825, https://support.apple.com/numbers
- **LibreOffice:** Mozilla Public License v2.0. Needs "macOS 11 or newer" on an "Intel or Apple silicon processor". VERIFIED. https://www.libreoffice.org/get-help/system-requirements/
- **Excel for Mac:** without Microsoft 365 or a perpetual licence, it runs in reduced-functionality or read-only mode and cannot save edits. CORROBORATED, but the sources are Microsoft Q&A community threads, not a formal Microsoft support article. https://learn.microsoft.com/en-us/answers/questions/5826750/mac-excel-home-wont-save-without-365-subscription, https://learn.microsoft.com/en-us/answers/questions/5666333/trouble-editing-in-excel-without-microsoft-365
- Excel for the web is free but runs in the cloud, so it conflicts with the rule that statement data never leaves the computer. VERIFIED that it is web-based; the conflict with the constraint is an inference.

### G. Python and Node on macOS

- **Python:** macOS does not ship a full Python 3. The Python docs say `/usr/bin/python3` links to "a usually older and incomplete version of Python provided by and for use by the Apple development tools, Xcode or the Command Line Tools for Xcode." They recommend the python.org installer, which can coexist with Apple's copy and takes precedence by default. VERIFIED. https://docs.python.org/3/using/mac.html
  - On a fresh Mac, typing `python3` brings up a prompt: "The 'python3' command requires the command line developer tools. Would you like to install the tools now?" CORROBORATED: Apple Community and Apple Developer Forums threads, plus MIT course notes. https://developer.apple.com/forums/thread/712657, https://discussions.apple.com/thread/252197784, https://smatz.mit.edu/6s090/info/python/installing/mac
- **Node.js** is not preinstalled on macOS. LIKELY: no Apple source ships it, and Tauri's docs tell users to download the LTS version from nodejs.org. Not directly verified this pass.
- **Practical install route for a non-specialist:** the python.org macOS installer (graphical, free) or the nodejs.org LTS installer (graphical, free). VERIFIED that the docs recommend these routes. Homebrew is an alternative, not researched this pass.

---

## Existing solutions and technologies referenced
- Flask, Uvicorn/FastAPI and Vite all listen only on this computer by default. Python `http.server` and bare Node `listen()` listen on the network by default.
- SQLite via Python `sqlite3` is standard. SQLCipher is free (BSD-3) but needs a source build or third-party packaging.
- Electron (MIT, macOS 13 Ventura or later) and Tauri v2 (needs Xcode and Rust, macOS 10.15 or later).
- Chart libraries: Chart.js (MIT), ECharts (Apache-2.0), uPlot (MIT), Recharts (MIT, React only).
- Spreadsheet fallbacks: Numbers (free), LibreOffice (MPL-2.0).

## Important limitations
- Python `http.server` and Node `listen()` without a host will expose the app on the local network unless the address is set explicitly.
- A browser-only app cannot write to a real file on disk in Safari or Firefox.
- SQLCipher encryption at $0 means building it or relying on third-party packaging, which is heavy for a non-specialist.
- Tauri needs a large toolchain (Xcode and Rust).
- Electron needs macOS 13 Ventura or later; the user's macOS version is UNKNOWN.
- Excel for Mac is not free to edit.

## Conflicting evidence
- None directly conflicting. The one caveat: Apple's security guide says all software is checked for known malware on first open "regardless of how it arrived", while Apple's engineer says Gatekeeper "usually only kicks in" for quarantined apps. These are compatible, because the malware scan and the signing/notarization block are different checks, but the formal docs do not state it explicitly.

## Unknowns
- The user's macOS version and chip (Apple silicon or Intel). This affects Electron's Ventura minimum and LibreOffice's macOS 11 minimum.
- Whether FileVault is turned on on the user's Mac, and whether it is on by default for consumer setups.
- Whether the macOS application firewall is on, and whether it would block an app listening on all interfaces.
- The exact AUD price of the Apple Developer Program (reported as A$149, unconfirmed). Not needed for a local-only app.
- Safari's Origin Private File System support. Not researched.
- Easy $0 install routes for SQLCipher on a Mac (Homebrew or Python bindings). Not researched.

## Research gaps
- Formal Apple documentation on ad-hoc signing for locally built apps on Apple silicon.
- Whether the python.org installer's bundled SQLite version supports everything the app needs (probably trivial for this app).
- The ECharts licence was confirmed only through search results for the GitHub and npm pages; I did not open its LICENSE file.

## Findings that materially affect architecture
1. **Network exposure depends on the server choice.** Flask, Uvicorn and Vite listen only on this computer by default. Python `http.server` and Node `listen()` without a host listen on all interfaces, so the address must be set to 127.0.0.1 explicitly. This bears directly on the rule that statement data never leaves the computer. (VERIFIED)
2. **A browser-only app cannot save to a real file in Safari or Firefox.** It can in Chrome and Edge. Otherwise it relies on evictable browser storage or manual export and import. (VERIFIED)
3. **Nothing needed to run a local app costs money.** Python, Node, SQLite, Electron and the chart libraries are all free. The Apple Developer Program is needed only to notarize an app for other people. An app built on the user's own Mac is unlikely to be blocked by Gatekeeper. (VERIFIED / CORROBORATED)
4. **Setup effort differs sharply between options.** Python needs one graphical installer. Tauri needs Xcode, Rust and Node. Encryption with SQLCipher means building from source. (VERIFIED)
5. **Encryption at rest is largely provided by the hardware.** Apple silicon and T2 Macs encrypt the disk automatically, and FileVault ties the key to the login password. Whether FileVault is on is UNCERTAIN and should be checked on the user's Mac, not assumed. This affects whether separate app-level encryption is worth its complexity.
6. **Recharts ties the app to React.** Chart.js, ECharts and uPlot work without a framework. (VERIFIED)

## Overall confidence
**High** for A, D, E (licences) and G (Python). Most claims come directly from official docs or repositories.

**Medium** for:
- B: FileVault default status is uncertain.
- C: Gatekeeper behaviour for locally built apps is CORROBORATED from an Apple engineer's forum post rather than formal documentation, and the AUD fee is unconfirmed.
- F: the Excel evidence comes from Microsoft Q&A community threads.
- Node's absence from macOS: LIKELY.

Sources:
- [Python http.server docs](https://docs.python.org/3/library/http.server.html)
- [Flask API docs](https://flask.palletsprojects.com/en/stable/api/)
- [Uvicorn settings (GitHub docs source)](https://github.com/encode/uvicorn/blob/master/docs/settings.md)
- [Node.js net docs](https://nodejs.org/api/net.html)
- [Vite server options](https://vite.dev/config/server-options)
- [Python sqlite3 docs](https://docs.python.org/3/library/sqlite3.html)
- [SQLCipher repo](https://github.com/sqlcipher/sqlcipher)
- [Apple: Protect data with FileVault](https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac)
- [Apple Platform Security: Volume encryption with FileVault](https://support.apple.com/guide/security/volume-encryption-with-filevault-sec4c6dc1b6e/web)
- [Apple Platform Security: Gatekeeper and runtime protection](https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web)
- [Apple Developer Forums thread 666452](https://developer.apple.com/forums/thread/666452)
- [Electron README](https://github.com/electron/electron/blob/main/README.md)
- [Electron build instructions macOS](https://www.electronjs.org/docs/latest/development/build-instructions-macos)
- [Tauri v2 prerequisites](https://v2.tauri.app/start/prerequisites/)
- [Apple Developer: compare memberships](https://developer.apple.com/support/compare-memberships/)
- [Apple Developer Program enroll](https://developer.apple.com/programs/enroll/)
- [MDN showSaveFilePicker](https://developer.mozilla.org/en-US/docs/Web/API/Window/showSaveFilePicker)
- [caniuse File System Access API](https://caniuse.com/native-filesystem-api)
- [Chart.js repo](https://github.com/chartjs/Chart.js)
- [Apache ECharts repo](https://github.com/apache/echarts)
- [ECharts npm](https://www.npmjs.com/package/echarts)
- [uPlot repo](https://github.com/leeoniya/uPlot)
- [Recharts repo](https://github.com/recharts/recharts)
- [LibreOffice system requirements](https://www.libreoffice.org/get-help/system-requirements/)
- [Numbers on Mac App Store](https://apps.apple.com/in/app/numbers/id409203825)
- [Numbers support](https://support.apple.com/numbers)
- [Microsoft Q&A: Excel Mac won't save without 365](https://learn.microsoft.com/en-us/answers/questions/5826750/mac-excel-home-wont-save-without-365-subscription)
- [Microsoft Q&A: editing Excel without 365](https://learn.microsoft.com/en-us/answers/questions/5666333/trouble-editing-in-excel-without-microsoft-365)
- [Python docs: Using Python on macOS](https://docs.python.org/3/using/mac.html)
- [Apple Developer Forums thread 712657](https://developer.apple.com/forums/thread/712657)
- [Apple Community thread 252197784](https://discussions.apple.com/thread/252197784)
- [MIT 6.s090 Python install on Mac](https://smatz.mit.edu/6s090/info/python/installing/mac)
