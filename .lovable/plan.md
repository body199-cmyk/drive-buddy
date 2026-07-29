## Goal

Reproduce the public repo `body199-cmyk/drive-companion` (TeleDrive v2) in this project, file for file. It is already a Lovable TanStack Start project on the same template, so the copy is direct — no porting needed.

## What the repo contains

1. **A real Python package** (`python-package/`, ~30 modules + 20 test files + mocks + docs) — TeleDrive: Telegram (Telethon) → Google Drive transfer engine with SQLite state, resumable uploads, retry policy, queue/transfer managers, checkpoints, Gradio UI, Arabic/English i18n.
2. **A Colab notebook** (`python-package/notebook/TeleDrive.ipynb`, also mirrored at `public/TeleDrive.ipynb`).
3. **A single-page web landing** (`src/routes/index.tsx`) listing the modules and offering two downloads: the package ZIP (`public/teledrive-package.zip`) and the notebook.
4. Shared UI kit (`src/components/ui/*`), the standard template files, and `.lovable/plan.md` (the Arabic build plan).

## Steps

1. **Fetch every file** from the repo at its current HEAD (raw download for text, binary-safe download for `public/teledrive-package.zip` and `public/favicon.ico`).
2. **Write the Python package** into `python-package/` exactly as-is: `teledrive/` modules, `locale/ar.json` + `en.json`, `tests/` with `mocks/`, `docs/{ARCHITECTURE,RUNBOOK,TROUBLESHOOTING}.md`, `requirements.txt`, `.env.example`, `README.md`, `CHANGELOG.md`, `HANDOFF.md`, and the notebook.
3. **Copy the public assets**: `public/TeleDrive.ipynb`, `public/teledrive-package.zip`, `robots.txt`, favicon.
4. **Copy the frontend**: `src/routes/index.tsx` (replaces the placeholder home page), `src/routes/__root.tsx`, `src/styles.css`, `src/components/ui/*`, `src/hooks`, `src/lib`, and config files (`components.json`, `tsconfig.json`, `vite.config.ts`, `eslint.config.js`) where they differ from the current template.
5. **Sync dependencies**: install any packages in the repo's `package.json` missing here (mostly Radix/shadcn primitives, `lucide-react`, `recharts`, `sonner`, `zod`, etc.). Do not touch `src/routeTree.gen.ts` — it regenerates.
6. **Verify**: run the build/typecheck, load the preview home page, and confirm both download links serve the ZIP and the notebook.

## Technical notes

- The Python package is inert here — it is shipped as downloadable source for Google Colab; nothing runs it server-side.
- `src/routeTree.gen.ts` and `bun.lock` are regenerated locally rather than copied.
- Files that are byte-identical to the current template are left alone.
