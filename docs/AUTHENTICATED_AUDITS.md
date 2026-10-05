# Authenticated website audits

Authenticated audits are opt-in. The session is created locally by an operator, stored only beneath `runtime/auth/`, and is ignored by Git. Credentials, cookies, and tokens must not be copied into source, reports, tests, or terminal output.

From the repository root, create a session with a headed installed Chrome window:

```powershell
uv run python scripts/create_authenticated_session.py --login-url http://4.209.241.167/auth/login --authenticated-url http://4.209.241.167/ --browser-channel chrome
```

Complete one sign-in attempt in the browser window and press Enter in the terminal only after a protected page is available. The utility never reads or submits form values. It records only redacted request metadata, response status, redirects, console errors, and failed requests under the ignored `runtime/auth/4.209.241.167/login-diagnostics/` directory. A failed attempt never writes `session.json`.

Use `--browser-channel chromium` to compare Playwright's bundled Chromium. The session-capture launcher does not install the collector's network routing and permits service workers; these choices are intentionally isolated from ordinary audits.

Run one bounded preflight before a full audit:

```powershell
uv run python scripts/authenticated_preflight.py http://4.209.241.167/ --login-url http://4.209.241.167/auth/login --storage-state runtime/auth/4.209.241.167/session.json
```

The preflight stops if the state is missing, malformed, expired, redirected to login, or receives an authentication failure. Its diagnostic screenshot and summary remain under the ignored `runtime/auth/` directory.

Use the state only for the authorized audit run:

```powershell
uv run python scripts/run_pipeline.py http://4.209.241.167/ --mode gtm --skip-vision --storage-state runtime/auth/4.209.241.167/session.json --auth-login-url http://4.209.241.167/auth/login
```

If an authenticated application needs a separately hosted, public API, authorize its exact origin for that one run. This is opt-in; scheme and port must match, and redirects to every other origin remain blocked:

```powershell
uv run python scripts/run_pipeline.py http://4.209.241.167/ --mode gtm --skip-vision --storage-state runtime/auth/4.209.241.167/session.json --auth-login-url http://4.209.241.167/auth/login --allowed-dependency-url http://4.209.37.93/
```

The approved origins are recorded in the run configuration without credentials or storage-state contents. A machine-injected `SSLKEYLOGFILE` device path is removed only from the spawned audit process when it would prevent OpenSSL or browser startup; the user's Windows environment is not changed.

When the authenticated application explicitly loads Google Fonts, visual-fidelity collection may opt into its two exact public origins as well:

```powershell
--allowed-dependency-url https://fonts.googleapis.com/ --allowed-dependency-url https://fonts.gstatic.com/
```

These remain run-scoped origin approvals; no font wildcard or global network exception is added.

Normal audits remain unchanged when `--storage-state` is omitted. The crawler, evidence collector, responsive checks, and preflight use fresh browser contexts that load the same local state, while the existing network policy and safe-interaction protections remain in force.
