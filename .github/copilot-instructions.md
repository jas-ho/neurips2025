# GitHub Copilot Instructions for NeurIPS Abstract Browser

## Project Overview

NeurIPS Abstract Browser displays NeurIPS 2025 conference papers (orals and posters). Uses bd (beads) for issue tracking.

## Issue Tracking with bd

**CRITICAL**: Use **bd** for ALL task tracking. Do NOT create markdown TODO lists.

### Essential Commands

```bash
bd ready                           # Unblocked issues
bd create "Title" -t task -p 2     # Create issue
bd update <id> --status in_progress
bd close <id> --reason "Done"
bd sync                            # Sync at end of session
```

### Workflow

1. Check ready work: `bd ready`
2. Claim task: `bd update <id> --status in_progress`
3. Work on it
4. Complete: `bd close <id> --reason "Done"`
5. Sync: `bd sync`

## Tech Stack

- **Language**: Python 3.11+
- **Package Manager**: uv (inline dependencies via PEP 723)
- **Output**: Single self-contained HTML viewer

## Common Commands

```bash
# Build viewer
uv run scripts/build_viewer.py

# Generate similarity data
uv run scripts/enrich_embeddings.py
```

## Important Rules

- Use bd for ALL task tracking
- Run `bd sync` at end of sessions
- Do NOT create markdown TODO lists

See AGENTS.md for more details.
