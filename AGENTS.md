# Agent Instructions for NeurIPS Abstract Browser

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Quick Start

```bash
# Check for ready work
bd ready

# Create new issues
bd create "Issue title" -t bug|feature|task -p 0-4

# Claim and update
bd update <id> --status in_progress

# Complete work
bd close <id> --reason "Completed"

# Sync at end of session
bd sync
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Sync**: Run `bd sync` at end of session

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Run `bd sync` at end of sessions
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use the TodoWrite tool for task tracking
