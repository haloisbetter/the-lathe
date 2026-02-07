"""
Headless smoke test for Lathe TUI client.

Verifies HTTP connectivity to lathe_app.server without starting the TUI.
Prints SMOKE_OK on success.

Usage:
    python -m lathe_tui --smoke [--url URL]
    python lathe_tui/tools/smoke.py
"""
import os
import sys


def run_smoke(base_url: str | None = None) -> bool:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from lathe_tui.app.client import LatheClient

    url = base_url or os.environ.get("LATHE_URL", "http://127.0.0.1:3001")
    client = LatheClient(base_url=url)
    errors = []

    print(f"Smoke test against {url}")
    print("=" * 50)

    print("[1/4] Health check...", end=" ")
    health = client.health()
    if health.get("error_type"):
        print(f"FAIL: {health.get('message')}")
        errors.append("health")
    else:
        print("OK")

    print("[2/4] List runs (limit=5)...", end=" ")
    runs = client.runs_list(params={"limit": 5})
    if runs.get("error_type"):
        print(f"FAIL: {runs.get('message')}")
        errors.append("runs_list")
    else:
        run_list = runs.get("runs", [])
        print(f"OK ({len(run_list)} runs)")

        if run_list:
            first_id = run_list[0].get("id", run_list[0].get("run_id"))
            if first_id:
                print(f"[3/4] Fetch run detail ({first_id})...", end=" ")
                detail = client.runs_get(first_id)
                if detail.get("error_type"):
                    print(f"FAIL: {detail.get('message')}")
                    errors.append("runs_get")
                else:
                    print("OK")
            else:
                print("[3/4] Skip (no run ID)")
        else:
            print("[3/4] Skip (no runs)")

    print("[4/4] Health summary...", end=" ")
    summary = client.health_summary()
    if summary.get("error_type"):
        print(f"FAIL: {summary.get('message')}")
        errors.append("health_summary")
    else:
        print("OK")

    print("=" * 50)
    if errors:
        print(f"SMOKE_FAIL: {len(errors)} check(s) failed: {', '.join(errors)}")
        return False
    else:
        print("SMOKE_OK")
        return True


if __name__ == "__main__":
    success = run_smoke()
    sys.exit(0 if success else 1)
