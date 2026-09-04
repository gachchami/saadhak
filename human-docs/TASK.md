# Task 2 — Human-facing documentation for Saadhak

**Owner:** a human (Dhaval). **Audience:** judges, teammates, future contributors, and Dhaval-in-three-months.
**Location:** this directory, `human-docs/`. Agents are instructed to ignore it (see `CLAUDE.md` and the `.aiexclude`, `.cursorignore`, `.codeiumignore` files at the repo root). It is not a source of truth for code; it explains the app to people.

## Goal
Produce and keep current three documents that let a reader understand, run, and extend Saadhak without reading the code:

1. `README.md` — what the app is, how it thinks, how to run it, how to read the dashboard, glossary.
2. `API.md` — every interface the app exposes or depends on: the `saadhak` command line, the state-file and journal-record schemas the dashboard reads, the optional HTTP endpoints, and the Alpaca endpoints/tools/CLI commands used, with the exact call shapes.
3. `USER_STORIES.md` — personas and stories with acceptance criteria, mapped to the hackathon judging criteria.

Draft v0 of each file is already here, derived from `PLAN.md`. They describe the design as planned, not as built.

## Cadence
Update after each milestone in `PLAN.md` §6:
- Wed 18:45 IST: after the first dry-run loop (CLI commands and state schema settle).
- Thu 11:30 IST: after calibration + reconciliation ship (journal record fields settle).
- Thu 14:00 IST: after the dashboard deploys (screens and URL).
- Fri 12:00 IST: final pass alongside the write-up; copy the final numbers in.

## Acceptance criteria
- A reader can run the agent in dry-run mode in under five minutes using only `README.md`.
- Every `saadhak` subcommand and every `ops/*.sh` script appears in `API.md` with arguments, output shape, and exit codes.
- Every journal record type has a schema block with an example that was actually emitted by the running system.
- Every user story lists the evidence a judge can click on (dashboard section, journal file, video timestamp).
- No secrets, no account keys. The paper account ID may appear (it is part of the submission).

## Sources of truth to pull from
- `PLAN.md` (design intent) · `saadhak/cli.py` (commands) · `saadhak/witness/journal.py` (record schemas) · `state/latest.json` (dashboard contract) · `ops/*.sh` (CLI usage) · `docs/write-up.md` (final narrative).

## How to hand this to an agent anyway
If you ever want an agent to update these files, name the directory explicitly in the request ("update human-docs/API.md from cli.py"). The ignore rule in `CLAUDE.md` yields to an explicit instruction.
