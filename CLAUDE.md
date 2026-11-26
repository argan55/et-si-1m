@AGENTS.md

## Pour Claude Code
- Le contexte du projet et la section « État » sont dans `AGENTS.md` (importé ci-dessus). Mettre à jour « État » **dans `AGENTS.md`**, jamais ici.

<!-- delegation-kit:start -->
## Delegation setup for this project (jeu-1m, "Et si… ?")

Stack: Python simulation engine (FastAPI) + React front end. Follow the global delegation policy and the `orchestrer` skill.
First time only: read pyproject/requirements and package.json, then correct the commands and globs below to the real ones.

This project has its own `.venv` and `node_modules` inside the project folder, so EVERY delegation here uses `--isolation branch` (a worktree would lack them and Cline would get stuck).

Verification commands (adjust if different):
- Backend: `.venv\Scripts\python.exe -m pytest -q` (use the project's venv interpreter, not the system `python`)
- Frontend: `npm run build` (add `npm test` if tests exist)

Good candidates for Cline / simple-executor:
- unit tests for existing engine functions (`--allow "tests/*.py"` or the real tests folder)
- hand-written game events as data entries, following an existing example event
- UI strings / English translations (`--allow` the i18n files only)
- small, presentational React components with a given props interface

Keep for yourself (Claude): simulation engine design, balance issues (Hong Kong, Brazil-Mexico), event-engine logic, API contracts between FastAPI and React, deployment on Render.
<!-- delegation-kit:end -->
