# CLAUDE.md — Assistant Operating Guide for This Repo

> This file tells the assistant how to work on this project across sessions.

## Session Rituals

CHANGELOG.md exists in the context/ dir. This dir should be used for any references you need. There will also be a context/docs/ dir to contain specifics regarding the code itself.

### Before every chat
1. **Read `CHANGELOG.md`** (entire file) to recover context, the last plan, and pending next steps.
2. If `CHANGELOG.md` is missing, **create it** using the template in “Changelog Policy & Format”.

### After every chat
1. **Append a new entry** to `CHANGELOG.md` summarizing:
   - Chat timestamp (local), short topic, and participants (if applicable).
   - **Specifications / intent** agreed during the chat.
   - **Changes made** (files touched, functions added/modified, noteworthy diffs).
   - **Open questions / blockers** and **Next actions**.
2. **Rotate to the last 10 entries** (keep the 10 most recent; delete older entries from the file so context stays small).
3. If **substantial changes** were made (see “Commit Discipline”), run a commit.

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

If changes are **not** substantial, you may batch them until they are, but always record them in `CHANGELOG.md`.

---

## Destructive/Sensitive Operations

- **NEVER delete files automatically.** Do **not** run `rm`, `del`, or equivalent without explicit user confirmation.
- If deletion is requested or implied:
  1. **List the exact files/paths** to be removed.
  2. Ask: “Proceed to delete these files? Would you like me to commit current changes first?”
  3. If user opts in, **commit first**, then delete.
  4. Prefer safe moves (e.g., to an `/.archive` or system trash) when feasible.

---

## Changelog Policy & Format

- File: `CHANGELOG.md` at the repo root.
- Maintain a **stack of the last 10 chat entries only** (newest at top). When adding the 11th, drop the oldest.
- Keep entries concise but complete; link to files/lines when possible.

### `CHANGELOG.md` Entry Template (append at top)
```md
## [YYYY-MM-DD HH:MM] — <Short Topic>
### Spec / Intent
- <bullet points of requirements/decisions>

### Changes Made
- Files: <file1>, <file2> …
- Summary: <what changed and why>

### Next Actions
- <actionable next steps>

### Notes
- <open questions, risks, TODOs>
