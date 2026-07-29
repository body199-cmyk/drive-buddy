# Changelog

## v1.0.0 — 2026-07-29

- Initial release per Constitution v2.0.
- Telethon user-account client + Google Drive OAuth Desktop.
- SQLite (WAL) + atomic checkpoints exported to Drive `TeleDrive_AppData`.
- State machine with 12 states and strict transitions.
- Concurrency Safe/Balanced/Fast/Manual, hard cap 4.
- Retry: 5 attempts, base 2s, x2, cap 60s, jitter, transient-only.
- FloodWait honored, reauth surfaced, duplicates detected via `appProperties.source_key`.
- Gradio UI in Arabic + English (live toggle, RTL for Arabic).
- 6-cell Colab notebook, camera cell handoff generator, maintenance cell.
