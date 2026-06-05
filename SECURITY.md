# Security Policy

Armour is a defensive evaluation framework for tool-using AI agents. The repo
contains synthetic traces and abstract tool calls; it should not be used for
live target scanning, credential harvesting, exploit development, or production
automation.

## Reporting Issues

For ordinary bugs, open a GitHub issue with:

- the command you ran
- the trace or minimal fixture needed to reproduce the issue
- the expected and actual result
- your Python version

For security-sensitive issues, do not post secrets, live credentials, private
logs, or exploit payloads in a public issue. Use GitHub private vulnerability
reporting if it is available for the repository. If not, open a minimal public
issue saying that a private security report is needed, without including the
sensitive details.

## Secret Handling

- Never commit API keys.
- Never put real keys in README examples, benchmark reports, datasets, shell
  command arguments, or tracked `.env` files.
- Use local process environment variables such as `GEMINI_API_KEY`,
  `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`.
- Run `python3 scripts/check_no_secrets.py` before committing.
- If a key appears in a screenshot, chat transcript, or terminal log, rotate it.

## Responsible Use

Contributions should remain defensive and reproducible. Do not submit traces or
fixtures that include real personal data, real customer data, live secrets,
active target identifiers, or instructions for abusing third-party systems.
