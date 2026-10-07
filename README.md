# Career Memory Assistant

An MIT-licensed local assistant for preparing job applications from approved career facts. It never applies for jobs, sends messages or requests connections.

## Start in chat

Normal use happens in Claude or ChatGPT. Install the Claude `.mcpb` extension or follow the [chat connection instructions](#chat-first-installation-no-application-ui-required). The standalone browser UI below is optional for testing or reviewing your bank. GitHub provides the code; downloading it alone does not connect a chat account.

## Optional browser interface

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
2. Answer the accomplishment questionnaire, which begins by asking about awards and honors, and save individual statements with explicit storage consent. Choose **Awards & Honors** for these facts, with the awarding organization, award name and date. This optional section appears in both resume formats only when it has approved facts. Enter employer, role, dates and location. Approve the statement and context before resume use. Inspect, edit, export or delete facts at any time.
3. Discover jobs on a named Greenhouse or Lever employer board, on employer pages with JobPosting JSON-LD, or via your own LinkedIn MCP server. Strict results require an evidenced publication timestamp within the rolling past 14 days and an active check within 15 minutes. Unknown dates are excluded visibly. Greenhouse's `updated_at` is never treated as publication; Lever's documented public postings response lacks a reliable original publication timestamp. Employer JSON-LD needs a timezone-bearing `datePosted` and future `validThrough` to qualify. The latter is a conservative structured availability signal, not proof an application will be accepted.
4. Supply public company/team pages for cited evidence. Relevant JSON-LD Person records with title and employer can produce explicitly inferred possible teammates. The app does not claim a person is on the hiring team. Missing evidence returns `not found`. Non-structured pages remain available as cited excerpts for manual review.
5. Paste a target job description. Tailoring ranks approved facts by keyword overlap and keeps the statements verbatim. It does not use a language model or rewrite facts. Approve your identity details, generate PDF/DOCX, and review the statement trace before submitting yourself.

## Chat-first installation (no application UI required)

The assistant is an MCP tool server: the chat model conducts the conversation and calls the tools. Initialization supplies workflow instructions; the `career_interview` prompt and `start_career_session` tool begin the interview. The first question asks about awards and honors. Returning users can reuse their existing bank. Proposed statements must be shown and approved before resume use; saving requires explicit consent. Client compliance with conversational instructions depends on the model, while consent/approval flags are enforced by the backend.

### Claude Desktop: extension

Download `career-memory-assistant.mcpb` from the project release (or build it below). In Claude Desktop, open Settings → Extensions → Advanced settings → Install Extension and select the file. Choose a private data folder. Start a chat with “Use Career Memory Assistant to help build my career bank.” No separate app UI is needed.

The extension uses MCPB 0.4's UV runtime to install Python and dependencies. It is validated for macOS only; actual installation in Claude Desktop has not yet been exercised. Network access is needed for initial dependency installation. The optional LinkedIn command is a JSON command array for a trusted server you configure yourself; it never contains cookies. The current file parser uses POSIX resource limits, so Windows support is not claimed.

Build the source-only bundle from a checkout:

```sh
python tools/build_bundle.py career-memory-assistant.mcpb
```

For manifest validation use the official `@anthropic-ai/mcpb` CLI: `mcpb validate manifest.json`. The bundle includes source and package dependencies declared in pyproject, never private memory, working files or an authenticated browser profile.

### Claude Desktop or Codex: manual local connection

Install the Python package first. Generate a configuration snippet:

```sh
career-assistant-setup claude --output career-memory-config.json
```

Merge only its `career-memory` entry into your client's existing MCP settings; do not replace other servers. The command never modifies existing client settings and refuses to overwrite an output file. Claude Desktop developer settings can open its configuration file. Restart the client after merging. The configuration uses the installed environment's absolute Python path. The local server can also be run directly with `career-assistant-mcp`.

### ChatGPT (or Claude remote connector): OAuth HTTP connection

Each installation serves **one owner's bank**. This is not a shared multiuser SaaS. Every authorized client sees that owner's bank; run separate instances and private data directories for separate owners. HTTP uses the official MCP SDK's streaming HTTP transport, OAuth authorization-code flow with PKCE, dynamic client registration, resource-bound tokens, refresh rotation and revocation. A randomly generated pairing secret approves each new connection. Restarting the service revokes all connections and download links; reconnect afterward. No OpenAI/Anthropic inference API key is needed by this server.

Create a private pairing secret, then start the connection service behind an HTTPS reverse proxy you control:

```sh
career-assistant-setup pairing
career-assistant-connect --base-url https://career.your-domain.example --port 8767
```

Replace the example origin with your actual domain. The listener binds to `127.0.0.1`, not a public interface. Configure the reverse proxy to forward `/mcp`, `/.well-known/*`, `/authorize`, `/register`, `/token`, `/revoke`, `/pair`, and `/files/*` to port 8767, preserving Host. Disable access/query/body logging for these routes. OAuth request bodies are limited to 4 KB by the server; also limit them to 4 KB at the proxy. Limit MCP requests to 8 MB at the proxy. Use a private OS account/data folder and protect the proxy with deployment-level rate limits. The legacy port 8765 web interface must remain loopback-only.

In ChatGPT's custom MCP settings, add `https://your-actual-domain/mcp`, select OAuth, and complete the connection approval page using the secret from the private file named by setup. Do not paste the secret into chat. After authorization, ask “Use Career Memory Assistant to start my interview.” This setup requires permission to add custom MCP servers in your ChatGPT account/workspace. Claude remote connectors can use the same OAuth HTTP endpoint.

For supported OpenAI accounts, a Secure MCP Tunnel can carry the private MCP connection instead of public ingress. Follow the official tunnel guide to provision and link the tunnel to your workspace; this repository does not provision it or ask for your API key. Its browser-facing OAuth approval endpoint and signed download URLs must still be reachable by the user; the tunnel alone does not make those pages public. Prefer the HTTPS setup above if you need direct download links. No cloud deployment or account connection is performed automatically.

### Attachments and generated files

Attach a resume in the chat client's normal way. If the model can read it, it passes the actual extracted text to `resume_text`; the tool returns untrusted text for review without persisting it. `upload_resume` accepts actual base64 file bytes when available. If the client cannot access the attachment, the assistant asks for pasted text; it must not invent file bytes. No arbitrary remote file fetching or unrestricted local file-reading tool is exposed.

On HTTP, `export_resume` returns PDF, Word and trace links valid for 15 minutes. These signed links grant anyone holding them temporary file access: do not share them with unintended recipients. Deleting/replacing the file or restarting the server invalidates them. On local stdio, exports return absolute local paths and `career://exports/...` resource URIs; `read_resume_file` returns an embedded MCP file resource. Whether a client displays an attachment/download button depends on its file capabilities. Resources/local paths are not public links. Regenerate an export if a link expires.

Official connection references: [Claude desktop extensions](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop), [MCPB specification](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md), [ChatGPT custom MCP servers](https://developers.openai.com/api/docs/guides/custom-mcp-server), [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## LinkedIn dependency and authentication

The adapter uses the official Python MCP client and discovers server tools before calling them. Configure a command as a JSON array in the environment of your app or MCP server, for example:

```sh
export CAREER_LINKEDIN_COMMAND='["uvx","mcp-server-linkedin@4.26.2","--transport","stdio","--timeout","10000","--tool-timeout","180"]'
```

Optional operator environment settings can be passed using `CAREER_LINKEDIN_ENV`, a JSON object of string names and values (for example `{"UV_TOOL_DIR":"/absolute/local/package-directory"}`). It is never accepted from HTTP or tool arguments. Keep credentials out of tracked configuration.

This is an optional third-party dependency, not redistributed by this repository. Each user installs and authenticates their own server, using its official setup instructions. Do not paste cookies or credentials into this repo. Commands are operator configuration, never accepted from HTTP or tool arguments. Authentication, captcha and two-factor steps belong to the user; failures are reported without bypasses. Avoid concurrently opening another browser server against a session already in use by a client.

Only `search_jobs`, `get_job_details`, `get_company_profile`, `get_company_employees`, and `search_people` may be called. No write tools are exposed. LinkedIn search is bounded to one page and ten detail calls. `past_month` search is only candidate discovery: the strict 14-day filter is independent. The current plugin returns human-readable dates; the adapter deliberately returns these as excluded untrusted evidence until reliable original publication and active status fields can be normalized. It does not guess a publication date from `9 hours ago`, promotion, reposting, related-job sections, or first discovery.

**Validation:** installed plugin 4.26.2 live `search_jobs` and `get_job_details` worked during initial implementation. Subsequent end-to-end testing completed the application's actual live MCP handshake, but its search was blocked by an existing browser-profile lease held by another client. The official `close_session` tool also reported busy and left the saved session unchanged. Release or restart the owning server from its original chat, then retest search and one detail. No successful live adapter job read is claimed. Synthetic protocol tests still validate adapter calls, exclusions and safe actionable failures. No live results or account data are bundled.

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

22 tests cover consent, user isolation, persistence, edit/deletion, approval and statement trace, untrusted instruction text, upload limits/ZIP expansion, freshness boundaries/reposts/updates/unknown dates/inactive listings, SSRF, local authentication/host/origin checks, safe filenames, PDF/DOCX contents, real MCP handshake and client adapter calls against a synthetic server. No network account or cookies are needed for tests. Browser tests also covered actual PDF and DOCX uploads, approved fact editing, refresh and server-restart persistence, memory export/deletion, strict fixture jobs, real public company evidence, possible teammate inference from an explicitly synthetic source, and real PDF/DOCX downloads. Downloaded bytes matched the server files and both exports were rendered and visually inspected.

Official integration references:

- [LinkedIn MCP server](https://github.com/stickerdaniel/linkedin-mcp-server)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever public Postings API](https://github.com/lever/postings-api)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## Public release

MIT source is ready for review, not published. Before launch: audit every staged file and Git history for private data; add reproducible dependency locking and CI on supported operating systems; validate live adapter setup using a separate test user's authentication; assess dependency vulnerabilities; add any required cloud auth/isolation before hosting. The app is a usable local MVP, not an Internet-facing multiuser service.

Chat connection tests also cover a real HTTP MCP handshake, OAuth discovery/registration/PKCE/pairing, consent and identity approval gates, resume resources/downloads, tampered/expired/replaced-file links, refresh rotation, revocation, and configuration preservation. ChatGPT/Claude account installation and public HTTPS connectivity are not yet live-tested.
