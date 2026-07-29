"""One-command launcher for Google Colab.

    !python teledrive_launcher.py

Bootstraps the single ApplicationContext, verifies the binding contract and
launches the Gradio interface with a public link.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from teledrive.app import launch  # noqa: E402
from teledrive.bootstrap import bootstrap  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="TeleDrive v3.1 launcher")
    parser.add_argument("--no-share", action="store_true", help="do not create a public link")
    parser.add_argument("--check", action="store_true", help="verify bindings and exit")
    args = parser.parse_args()

    ctx = bootstrap()
    print("bootstrap:", ctx.bootstrap_info)

    if args.check:
        from teledrive import action_registry

        for spec in action_registry.ready_specs():
            ctx.resolve(spec.service_path)
        print(f"binding check ok: {len(action_registry.ACTION_SPECS)} actions resolve")
        return 0

    launch(share=not args.no_share)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
