"""
Packaging regression tests.

Fails if lathe_app is not importable after install,
or if pyproject.toml omits required packages.
Fast, offline, no PYTHONPATH dependency.
"""
import importlib
import tomllib
from pathlib import Path


def test_lathe_is_importable():
    mod = importlib.import_module("lathe")
    assert hasattr(mod, "__file__")


def test_lathe_app_is_importable():
    mod = importlib.import_module("lathe_app")
    assert hasattr(mod, "__file__")


def test_lathe_app_subpackages_importable():
    for name in ["lathe_app.workspace", "lathe_app.knowledge", "lathe_app.goals"]:
        mod = importlib.import_module(name)
        assert hasattr(mod, "__file__"), f"{name} not importable"


def test_pyproject_declares_both_packages():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        config = tomllib.load(f)

    packages_cfg = config.get("tool", {}).get("setuptools", {}).get("packages", {})

    if isinstance(packages_cfg, list):
        assert "lathe" in packages_cfg, "pyproject.toml must declare lathe package"
        assert "lathe_app" in packages_cfg, "pyproject.toml must declare lathe_app package"
        return

    if isinstance(packages_cfg, dict) and "find" in packages_cfg:
        includes = packages_cfg["find"].get("include", [])
        has_lathe = any("lathe" in i for i in includes)
        has_lathe_app = any("lathe_app" in i for i in includes)
        assert has_lathe, "pyproject.toml packages.find must include lathe"
        assert has_lathe_app, "pyproject.toml packages.find must include lathe_app"
        return

    assert False, "pyproject.toml must declare both lathe and lathe_app packages"
