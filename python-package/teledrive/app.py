"""Entry point: launches the Gradio UI. Colab-friendly inline launch."""
from __future__ import annotations

from . import bootstrap
from .config import CONFIG
from .logging_config import get_logger
from .ui import build

_log = get_logger("teledrive.app")


def launch(share: bool = False, inline: bool = True) -> None:
    bootstrap.run()
    if share:
        from .i18n import t
        _log.warning(t("msg.share_warning"))
    demo = build()
    demo.launch(share=share, inline=inline, quiet=True)
