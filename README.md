# Career Memory Assistant

An MIT-licensed local assistant for preparing job applications from approved career facts. It never applies for jobs, sends messages or requests connections.

## Start

Python 3.11 or newer is required (macOS/Linux; upload resource limits currently use POSIX).

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
career-assistant
```

Open the authenticated URL printed in the terminal. The local interface listens only on `127.0.0.1:8765`. Treat the URL token like a password. A new token is generated at each startup. The token stays in this browser tab session for refreshes; after a server restart, reopen the new authenticated URL.

In the prepared review workspace, dependencies are already available:

```sh
CAREER_DATA_DIR="$PWD/work/local-private" work/venv/bin/python -m career_assistant.web
```

Stop the running review server before starting another on port 8765, or add `--port 8766`. The review instance is empty and stores data under ignored `work/local-private`.

## Workflow

1. Upload a PDF, DOCX or UTF-8 text resume. Extraction is temporary; the original file is never stored. Scanned PDFs need text recognition outside this app. File size: 5 MB; PDFs: 30 pages; expanded DOCX: 20 MB. Parsers run in a subprocess with a 20-second timeout and CPU/memory limits where supported.
2. Answer the accomplishment questionnaire and save individual statements with explicit storage consent. Enter employer, role, dates and location. Approve the statement and context before resume use. Inspect, edit, export or delete facts at any time.
3. Discover jobs on a named Greenhouse or Lever employer board, on employer pages with JobPosting JSON-LD, or via your own LinkedIn MCP server. Strict results require an evidenced publication timestamp within the rolling past 14 days and an active check within 15 minutes. Unknown dates are excluded visibly. Greenhouse's `updated_at` is never treated as publication; Lever's documented public postings response lacks a reliable original publication timestamp. Employer JSON-LD needs a timezone-bearing `datePosted` and future `validThrough` to qualify. The latter is a conservative structured availability signal, not proof an application will be accepted.
4. Supply public company/team pages for cited evidence. Relevant JSON-LD Person records with title and employer can produce explicitly inferred possible teammates. The app does not claim a person is on the hiring team. Missing evidence returns `not found`. Non-structured pages remain available as cited excerpts for manual review.
5. Paste a target job description. Tailoring ranks approved facts by keyword overlap and keeps the statements verbatim. It does not use a language model or rewrite facts. Approve your identity details, generate PDF/DOCX, and review the statement trace before submitting yourself.

## MCP

A real MCP SDK server exposes career memory, questionnaire, upload, discovery, research, tailoring, export and allowlisted LinkedIn reads over stdio.

Example local MCP client configuration (replace the absolute paths):

```json
{
  "mcpServers": {
    "career-memory": {
      "command": "/absolute/path/.venv/bin/python",
      "args": ["-m", "career_assistant.mcp_server"],
      "env": {
        "CAREER_USER": "local",
        "CAREER_DATA_DIR": "/absolute/private/career-data"
      }
    }
  }
}
```

Install the package in that environment first; the client working directory need not be the repo. Tool schemas and docstrings describe arguments. `career_operations` lists all operations. For example `career_memory(action="save", arguments={"fact":{"text":"Led launch workshops","approved":true},"consent":true})`.

This stdio server is usable by local MCP clients such as Codex. A cloud ChatGPT custom connector requires an authenticated reachable HTTP MCP service; this MVP does **not** expose a public endpoint or implement OAuth. Never tunnel the local interface publicly. Production cloud support requires a dedicated deployment with OAuth, tenant identity derived from authentication, quotas and secure file downloads.

## LinkedIn dependency and authentication

The adapter uses the official Python MCP client and discovers server tools before calling them. Configure a command as a JSON array in the environment of your app or MCP server, for example:

```sh
export CAREER_LINKEDIN_COMMAND='["uvx","mcp-server-linkedin@4.26.2","--transport","stdio","--timeout","10000","--tool-timeout","180"]'
```

This is an optional third-party dependency, not redistributed by this repository. Each user installs and authenticates their own server, using its official setup instructions. Do not paste cookies or credentials into this repo. Commands are operator configuration, never accepted from HTTP or tool arguments. Authentication, captcha and two-factor steps belong to the user; failures are reported without bypasses. Avoid concurrently opening another browser server against a session already in use by a client.

Only `search_jobs`, `get_job_details`, `get_company_profile`, `get_company_employees`, and `search_people` may be called. No write tools are exposed. LinkedIn search is bounded to one page and ten detail calls. `past_month` search is only candidate discovery: the strict 14-day filter is independent. The current plugin returns human-readable dates; the adapter deliberately returns these as excluded untrusted evidence until reliable original publication and active status fields can be normalized. It does not guess a publication date from `9 hours ago`, promotion, reposting, related-job sections, or first discovery.

**Validation:** installed plugin 4.26.2 live `search_jobs` and `get_job_details` worked during implementation. The application adapter's SDK handshake, tool discovery, calls and strict exclusions passed against a synthetic subprocess MCP server. End-to-end live adapter authentication is not claimed as validated. No live results or account data are bundled.

## Privacy and isolation

Default storage is `~/.local/share/career-assistant`, outside the checkout. Override with `CAREER_DATA_DIR` to choose another private location. Directory permissions are 0700 and files 0600. Separate operator-selected `--user` / `CAREER_USER` identities map to isolated hashed directories. Requests cannot choose another user. This is local operator isolation, **not a multiuser authentication system**: any process running as the same OS account can access the files. SQLite and exports are not encrypted; use OS disk encryption and protected backups for sensitive data.

Memory is inspectable, editable, exportable and deletable. SQLite secure deletion and vacuum remove deleted facts from the active database; filesystem snapshots/backups may retain data. The UI separately deletes generated resume files and traces. Deleting the entire selected user's directory removes memory, exports and public-job observations. Downloaded copies remain under your control.

External document and page text is untrusted data. The app never executes embedded instructions or runs an agent on that text. PDF/DOCX processing is bounded but is not an OS-level hostile-file sandbox; keep dependencies updated and use an isolated container for unknown high-risk documents. Resume PDFs with Western text use core Times/Helvetica fonts; DOCX requests system Times New Roman/Arial. No font binaries are bundled. PDF characters outside this fallback repertoire fail clearly instead of being corrupted. Names that cannot be transliterated for filenames use safe `candidate.unnamed` fallbacks.

Public requests permit HTTPS port 443 only, reject credentials and private/reserved DNS answers, pin the selected public IP for TLS, verify certificates, ignore proxies and refuse redirects. Responses are capped at 2 MB with timeouts. DNS rebinding cannot redirect the pinned connection into a private network. Host and origin checks, a random bearer token, no-store responses and a restrictive content policy protect the local interface. Access logs omit request details; third-party MCP stderr is suppressed. No secrets are shipped.

## Resume style

A4, centered uppercase serif name, headline/contact row, centered serif section headings with thin rules, left employer/role and right dates/location, compact sans-serif bullets, and automatic pagination instead of shrinking. The user's private reference was used for layout direction only and is not included. Fallback typography is disclosed. Volunteering uses the same paired context layout; languages use approved prose rather than inventing numeric proficiency ratings. Exact two-column volunteer cards and proficiency-dot controls are not implemented in this MVP.

Export filenames: `firstname.lastname.jobtitle.company.pdf`, `.docx`, and `.trace.json`; lowercase and hyphens within components. Examples are entirely fictional.

## Tests and development

```sh
python -m unittest discover -s tests -v
```

Tests cover consent, user isolation, persistence, edit/deletion, approval and statement trace, untrusted instruction text, upload limits/ZIP expansion, freshness boundaries/reposts/updates/unknown dates/inactive listings, SSRF, local authentication/host/origin checks, safe filenames, PDF/DOCX contents, real MCP handshake and client adapter calls against a synthetic server. No network account or cookies are needed for tests. PDF and DOCX samples were rendered and visually inspected.

Official integration references:

- [LinkedIn MCP server](https://github.com/stickerdaniel/linkedin-mcp-server)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever public Postings API](https://github.com/lever/postings-api)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## Public release

MIT source is ready for review, not published. Before launch: audit every staged file and Git history for private data; add reproducible dependency locking and CI on supported operating systems; validate live adapter setup using a separate test user's authentication; assess dependency vulnerabilities; add any required cloud auth/isolation before hosting. The app is a usable local MVP, not an Internet-facing multiuser service.
