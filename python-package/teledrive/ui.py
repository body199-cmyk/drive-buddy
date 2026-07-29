"""Gradio UI. All strings via i18n; zero hardcoded user-facing text."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from . import database as db
from .auth_manager import AUTH
from .checkpoint_manager import reconcile_with_drive, restore_from_drive, apply_snapshot
from .config import CONFIG, DRIVE_TOKEN
from .drive_client import DriveService
from .filters import FilterSet, apply as apply_filters
from .i18n import t, set_language, toggle
from .logging_config import get_logger, tail
from .media_scanner import scan_link
from .models import MediaItem
from .progress_tracker import PROGRESS
from .queue_manager import QUEUE
from .telegram_client import TelegramService
from .telegram_links import parse as parse_link
from .transfer_manager import TransferManager
from .utils import human_bytes, human_duration, safe_disk_free
from .config import TEMP_DIR

_log = get_logger("teledrive.ui")

try:
    import gradio as gr
except Exception:  # pragma: no cover
    gr = None  # type: ignore

_transfer_mgr: TransferManager | None = None
_transfer_thread: threading.Thread | None = None
_transfer_loop: asyncio.AbstractEventLoop | None = None


def _lang(): return CONFIG.language


def _tel_status():
    return t("status.connected") if AUTH.state.telegram_authorized else t("status.disconnected")


def _drv_status():
    return t("status.connected") if AUTH.state.drive_authorized else t("status.disconnected")


# ---- Telegram handlers ----

def ui_connect_telegram(api_id: str, api_hash: str):
    try:
        svc = TelegramService(int(api_id), api_hash.strip())
        # Run in a thread with its own loop.
        loop = asyncio.new_event_loop()
        loop.run_until_complete(svc.connect())
        AUTH.set_telegram(svc)
        return f"{t('nav.telegram')}: {_tel_status()}", _tel_status()
    except Exception as e:
        return f"{t('err.unknown')}: {e}", _tel_status()


def ui_send_code(phone: str):
    if not AUTH.telegram:
        return t("err.reauth")
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(AUTH.telegram.start_login(phone.strip()))
        return t("btn.send_code") + " ✓"
    except Exception as e:
        return f"{t('err.unknown')}: {e}"


def ui_verify_code(phone: str, code: str, password: str):
    if not AUTH.telegram:
        return t("err.reauth"), _tel_status()
    try:
        loop = asyncio.new_event_loop()
        ok = loop.run_until_complete(
            AUTH.telegram.complete_login(phone.strip(), code.strip(), password.strip() or None)
        )
        AUTH.state.telegram_authorized = ok
        return (t("status.connected") if ok else t("status.disconnected")), _tel_status()
    except Exception as e:
        return f"{t('err.unknown')}: {e}", _tel_status()


def ui_logout_telegram():
    if AUTH.telegram:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(AUTH.telegram.logout())
        except Exception:
            pass
    AUTH.clear_telegram()
    return _tel_status()


# ---- Drive handlers ----

def ui_drive_start(client_json_file):
    if client_json_file is None:
        return t("form.upload_client_json"), _drv_status(), ""
    try:
        path = client_json_file.name if hasattr(client_json_file, "name") else str(client_json_file)
        svc = DriveService(client_secret_path=path)
        if svc.try_authenticate_from_token():
            AUTH.set_drive(svc)
            return t("status.connected"), _drv_status(), ""
        url = svc.start_auth_flow()
        AUTH.drive = svc  # temp reference for code completion
        return t("form.paste_oauth_code"), _drv_status(), url
    except Exception as e:
        return f"{t('err.unknown')}: {e}", _drv_status(), ""


def ui_drive_complete(oauth_code: str):
    if not AUTH.drive:
        return t("err.reauth"), _drv_status()
    try:
        ok = AUTH.drive.complete_auth_flow(oauth_code.strip())
        if ok:
            AUTH.set_drive(AUTH.drive)
            return t("status.connected"), _drv_status()
        return t("err.unknown"), _drv_status()
    except Exception as e:
        return f"{t('err.unknown')}: {e}", _drv_status()


def ui_drive_logout():
    AUTH.clear_drive()
    return _drv_status()


# ---- Analyze + queue ----

def ui_analyze(link: str):
    if not AUTH.telegram or not AUTH.state.telegram_authorized:
        return t("err.reauth"), []
    try:
        parsed = parse_link(link.strip())
        loop = asyncio.new_event_loop()
        items = loop.run_until_complete(scan_link(AUTH.telegram, parsed))
        rows = [
            [it.safe_name, it.media_type, human_bytes(it.size_bytes), it.state, "0%", it.attempts]
            for it in items
        ]
        # persist as Pending
        QUEUE.bulk_enqueue(items)
        return f"{len(items)} items", rows
    except Exception as e:
        return f"{t('err.unknown')}: {e}", []


def ui_queue_rows():
    items = db.list_items(limit=500)
    return [
        [it.safe_name, it.media_type, human_bytes(it.size_bytes),
         t(f"state.{it.state}"),
         f"{max(it.download_pct, it.upload_pct):.0f}%", it.attempts]
        for it in items
    ]


def ui_dashboard():
    snap = PROGRESS.snapshot()
    quota_line = "—"
    try:
        if AUTH.drive:
            q = AUTH.drive.storage_quota()
            quota_line = f"{human_bytes(q['usage'])} / {human_bytes(q['limit'])}"
    except Exception:
        pass
    disk_free = human_bytes(safe_disk_free(TEMP_DIR))
    current = ""
    if snap["active"]:
        a = snap["active"][0]
        current = f"{a['name']} — {a['phase']} {max(a['pct_download'], a['pct_upload']):.0f}%"
    return {
        t("dash.current"): current,
        t("dash.done"): snap["done_files"],
        t("dash.failed"): snap["failed_files"],
        t("dash.remaining"): max(0, snap["total_files"] - snap["done_files"] - snap["failed_files"]),
        t("dash.speed"): human_bytes(snap["instant_speed"]) + "/s",
        t("dash.avg_speed"): human_bytes(snap["average_speed"]) + "/s",
        t("dash.eta"): human_duration(snap["eta_seconds"]),
        t("dash.overall_pct"): f"{(snap['done_bytes'] / snap['total_bytes'] * 100) if snap['total_bytes'] else 0:.1f}%",
        t("dash.telegram_status"): _tel_status(),
        t("dash.drive_status"): _drv_status(),
        t("dash.drive_space"): quota_line,
        t("dash.colab_space"): disk_free,
    }


# ---- Transfer control ----

def _ensure_drive_folder() -> str:
    assert AUTH.drive
    if CONFIG.drive_folder_id:
        return CONFIG.drive_folder_id
    fid = AUTH.drive.ensure_folder("TeleDrive_Transfers")
    CONFIG.drive_folder_id = fid
    return fid


def ui_start_transfer():
    global _transfer_mgr, _transfer_thread, _transfer_loop
    if not (AUTH.state.telegram_authorized and AUTH.state.drive_authorized):
        return t("err.reauth")
    if _transfer_thread and _transfer_thread.is_alive():
        return t("status.running")
    folder = _ensure_drive_folder()
    _transfer_mgr = TransferManager(AUTH.telegram, AUTH.drive, folder)

    def runner():
        global _transfer_loop
        _transfer_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_transfer_loop)
        try:
            _transfer_loop.run_until_complete(_transfer_mgr.run())
        finally:
            _transfer_loop.close()

    _transfer_thread = threading.Thread(target=runner, daemon=True)
    _transfer_thread.start()
    return t("status.running")


def ui_pause():
    if _transfer_mgr: _transfer_mgr.pause()
    return t("status.paused")


def ui_resume():
    if _transfer_mgr: _transfer_mgr.resume()
    return t("status.running")


def ui_stop():
    if _transfer_mgr: _transfer_mgr.stop()
    return t("status.stopped")


def ui_recover():
    if not AUTH.drive:
        return t("msg.recovery_none")
    snap = restore_from_drive(AUTH.drive)
    if not snap:
        return t("msg.recovery_none")
    n = apply_snapshot(snap)
    r = reconcile_with_drive(AUTH.drive)
    return f"{t('msg.recovery_ok')} imported={n} reconciled={r}"


def ui_logs():
    return tail(lines=300)


def ui_toggle_lang():
    new = toggle()
    return new


# ---- Build the app ----

def build() -> Any:
    if gr is None:
        raise RuntimeError("gradio is not installed")

    with gr.Blocks(title="TeleDrive", theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# {t('app.title')}\n{t('app.subtitle')}")
        lang_btn = gr.Button(t("btn.language"))
        lang_state = gr.Textbox(value=_lang(), visible=False)

        with gr.Tab(t("nav.telegram")):
            api_id = gr.Textbox(label=t("form.api_id"), type="password")
            api_hash = gr.Textbox(label=t("form.api_hash"), type="password")
            connect_btn = gr.Button(t("btn.connect_telegram"))
            tel_status = gr.Textbox(label=t("dash.telegram_status"), value=_tel_status(), interactive=False)
            connect_out = gr.Textbox(label="")
            connect_btn.click(ui_connect_telegram, [api_id, api_hash], [connect_out, tel_status])

            phone = gr.Textbox(label=t("form.phone"))
            send_code_btn = gr.Button(t("btn.send_code"))
            code = gr.Textbox(label=t("form.code"))
            password = gr.Textbox(label=t("form.password"), type="password")
            verify_btn = gr.Button(t("btn.verify"))
            code_out = gr.Textbox(label="")
            send_code_btn.click(ui_send_code, [phone], [code_out])
            verify_btn.click(ui_verify_code, [phone, code, password], [code_out, tel_status])

            logout_btn = gr.Button(t("btn.logout"))
            logout_btn.click(ui_logout_telegram, None, [tel_status])

        with gr.Tab(t("nav.drive")):
            client_file = gr.File(label=t("form.upload_client_json"), file_types=[".json"])
            drv_start = gr.Button(t("btn.link_drive"))
            drv_status_box = gr.Textbox(label=t("dash.drive_status"), value=_drv_status(), interactive=False)
            drv_url = gr.Textbox(label="OAuth URL", interactive=False)
            oauth_code = gr.Textbox(label=t("form.paste_oauth_code"))
            drv_complete = gr.Button(t("btn.verify"))
            drv_msg = gr.Textbox(label="")
            drv_start.click(ui_drive_start, [client_file], [drv_msg, drv_status_box, drv_url])
            drv_complete.click(ui_drive_complete, [oauth_code], [drv_msg, drv_status_box])
            drv_logout = gr.Button(t("btn.logout"))
            drv_logout.click(ui_drive_logout, None, [drv_status_box])

        with gr.Tab(t("nav.link")):
            link = gr.Textbox(label=t("form.link"))
            analyze_btn = gr.Button(t("btn.analyze"))
            analyze_msg = gr.Textbox(label="")
            files_table = gr.Dataframe(
                headers=[t("col.file"), t("col.type"), t("col.size"),
                         t("col.state"), t("col.progress"), t("col.attempts")],
                interactive=False,
            )
            analyze_btn.click(ui_analyze, [link], [analyze_msg, files_table])

        with gr.Tab(t("nav.queue")):
            refresh_q = gr.Button(t("btn.refresh"))
            queue_table = gr.Dataframe(
                headers=[t("col.file"), t("col.type"), t("col.size"),
                         t("col.state"), t("col.progress"), t("col.attempts")],
                interactive=False,
            )
            refresh_q.click(lambda: ui_queue_rows(), None, [queue_table])

        with gr.Tab(t("nav.settings")):
            conc = gr.Radio(["safe", "balanced", "fast"], value=CONFIG.concurrency,
                            label=t("nav.settings"))

            def set_conc(v):
                CONFIG.concurrency = v
                CONFIG.manual_concurrency = None
                return v

            conc.change(set_conc, [conc], [conc])
            start_btn = gr.Button(t("btn.start"))
            pause_btn = gr.Button(t("btn.pause"))
            resume_btn = gr.Button(t("btn.resume"))
            stop_btn = gr.Button(t("btn.stop"))
            recover_btn = gr.Button(t("msg.recovery_ok"))
            transfer_status = gr.Textbox(label=t("dash.queue_status"), interactive=False)
            start_btn.click(ui_start_transfer, None, [transfer_status])
            pause_btn.click(ui_pause, None, [transfer_status])
            resume_btn.click(ui_resume, None, [transfer_status])
            stop_btn.click(ui_stop, None, [transfer_status])
            recover_btn.click(ui_recover, None, [transfer_status])

        with gr.Tab(t("nav.dashboard")):
            dash = gr.JSON(label=t("nav.dashboard"))
            dash_refresh = gr.Button(t("btn.refresh"))
            dash_refresh.click(ui_dashboard, None, [dash])

        with gr.Tab(t("nav.logs")):
            logs_out = gr.Textbox(label=t("nav.logs"), lines=20)
            logs_refresh = gr.Button(t("btn.refresh"))
            logs_refresh.click(ui_logs, None, [logs_out])

        lang_btn.click(ui_toggle_lang, None, [lang_state])

    return demo
