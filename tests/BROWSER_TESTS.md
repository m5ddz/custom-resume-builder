# Browser acceptance tests

Run in an isolated disposable synthetic bank, never a user's real career bank:

```sh
PYTHONPATH=. python tests/browser_fixture_server.py --port 8766 --user synthetic-e2e
```

Open the authenticated local URL. Only reserved `https://qa.example/` URLs use synthetic fixtures. Other URLs call the production public HTTPS fetcher. This fixture server is not used by the installed application and its fixture pages are not real job/company results.

1. Generate fictional samples with `python examples/synthetic.py`. Upload the PDF and DOCX through the file chooser. Verify their text appears, no facts are stored automatically, and the seven questionnaire prompts appear.
2. Save a fictional accomplishment with consent and approval. Refresh; edit the statement, consent again, save, and ensure it updates rather than duplicates. Export memory and verify JSON contains the approved edited text. Restart the server, reopen its new authenticated URL, and verify facts remain.
3. Paste an untrusted job description asking for an invented doctorate or metric. Preview statements and check these requests do not become claims. Attempt export without identity approval (must fail), then approve fictional identity and generate both formats. Download both and verify filenames follow `firstname.lastname.jobtitle.company` with lowercase hyphenated components. Compare downloaded bytes with private server exports; check text and statement trace, render PDF and DOCX, and inspect every page.
4. Choose Employer job pages. Enter `https://qa.example/job-new`, a duplicate of that URL, `https://qa.example/job-old`, `https://qa.example/job-closed`, and `https://qa.example/job-unknown`. Expect one unique strict result. Expect stale/closed/unknown exclusions; unknown must be labelled updated with no publication evidence. First discovery must remain stable across refresh/restart.
5. Research `https://qa.example/team` for Product Marketing Manager. Expect cited fictional Alex Example and an explicitly inferred possible teammate relationship. Research a real public company page separately; any missing Person evidence must return `not found`.
6. Delete the fictional fact, verify it disappears in the interface and backend, and verify no facts remain after restart. Delete generated exports separately; old download links must clear or explain that regeneration is needed. Downloaded copies are independent of server deletion.
7. Inspect console errors and screenshots. Distinguish browser automation limitations from app failures: the in-app browser downloads native files without emitting the Playwright download event; verify the actual files instead. Modal button clicks may time out after executing; inspect resulting state before any retry.

Live LinkedIn is a separate, read-only integration test. Configure your own server command/environment; complete the MCP handshake, search one page, and read exactly one returned job. Do not persist raw account-aware responses or session artifacts. Relative dates, repost labels and related-job text must not be promoted to evidenced original publication dates. If the official server reports another browser owner, stop dependent reads and release the session from the owning chat/server before retrying. Do not remove locks or copy profiles.
