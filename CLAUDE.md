# CLAUDE.md — Assistant Operating Guide for This Repo

> This file tells the assistant how to work on this project across sessions.

## Session Rituals


### Before every chat
1. **Review recent git history** (`git log --oneline -10` or `git log --graph --oneline -20`) to recover context, the last plan, and pending next steps.
2. **Check for active session notes** in `docs/session-notes/` - read the most recent session file (e.g., `2024-12-30-session.md`) to resume in-progress work.
3. Check `docs/session-notes/CHANGELOG.md` for session history and continuity notes.
4. Check `docs/` for reference documentation including VBA analysis and guides.

### After every chat
1. If **substantial changes** were made (see "Commit Discipline"), run a commit with a descriptive message summarizing the work.

### Testing & Development
- **NEVER run `npm run dev` or development servers.** The user will handle all testing and server execution.
- **DO NOT** automatically start development processes or check server status.
- Focus on code changes only; user manages their own development environment.

---

## Commit Discipline

**Substantial change = any of:**
- Functional behavior changed or new feature added.
- Database schema / migrations modified.
- Public API, CLI flags, or file formats changed.
- Refactor exceeding ~30 lines in a file, or multi-file edits.
- Dependency or build config updated.

**Action:** after a substantial change:
1. `git add -A`
2. `git commit -m "<type>: <concise summary> (#ticket?)"`
   - Use Conventional Commit types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `build`.
3. If many related changes are pending deletion (see below), **offer to commit first** before any destructive step.

If changes are **not** substantial, you may batch them until they are.

---

## Code Standards

- **Imports must be at top of file.** Do not place import statements inside functions or methods. Use `TYPE_CHECKING` blocks for type-only imports that would cause circular dependencies.

---

## Destructive/Sensitive Operations

- **NEVER delete files automatically.** Do **not** run `rm`, `del`, or equivalent without explicit user confirmation.
- If deletion is requested or implied:
  1. **List the exact files/paths** to be removed.
  2. Ask: “Proceed to delete these files? Would you like me to commit current changes first?”
  3. If user opts in, **commit first**, then delete.
  4. Prefer safe moves (e.g., to an `/.archive` or system trash) when feasible.

