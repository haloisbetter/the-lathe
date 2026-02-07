"""
Lathe TUI entrypoint.

Usage:
    python -m lathe_tui [--url URL] [--poll SECONDS]
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="lathe-tui",
        description="The Lathe — Operator Console TUI",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Base URL for lathe_app server (default: http://127.0.0.1:3001 or LATHE_URL env)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=2.0,
        help="Polling interval in seconds for live console (default: 2)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run headless smoke test instead of TUI",
    )

    args = parser.parse_args()

    if args.smoke:
        from lathe_tui.tools.smoke import run_smoke
        success = run_smoke(base_url=args.url)
        sys.exit(0 if success else 1)

    from lathe_tui.app.tui import run_tui
    run_tui(base_url=args.url, poll_interval=args.poll)


if __name__ == "__main__":
    main()
