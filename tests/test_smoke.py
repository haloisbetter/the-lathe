import sys
from pathlib import Path

# Ensure repo root is on Python path (CI / WSL / Docker safe)
sys.path.append(str(Path(__file__).resolve().parents[1]))

from lathe.core.task import TaskSpec


def test_smoke():
    task = TaskSpec(
        id="smoke-001",
        goal="Smoke test",
        scope="none",
        constraints={},
        inputs={},
    )

    assert task.id == "smoke-001"