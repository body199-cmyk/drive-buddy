"""Entry point: launches the Gradio UI on the single ApplicationContext."""
from __future__ import annotations

from . import bootstrap
from .app_context import ApplicationContext
from .logging_config import get_logger
from .ui import build

_log = get_logger("teledrive.app")


def launch(share: bool = False, inline: bool = True) -> ApplicationContext:
    ctx = bootstrap.run()
    if share:
        from .i18n import t

        _log.warning(t("msg.share_warning"))
    demo = build(ctx)
    demo.launch(share=share, inline=inline, quiet=True)
    return ctx
