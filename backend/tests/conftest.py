from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _set_test_env(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    monkeypatch.setenv("GITHUB_MODELS_TOKEN", "test-token")
    monkeypatch.setenv("USE_APOLLO_REAL_API", "false")
    monkeypatch.setenv("USE_SALESFORCE_WRITE_BACK", "false")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("PERSIST_OUTPUT", "false")
    monkeypatch.setenv("GITHUB_MODELS_TIMEOUT_SECONDS", "1")
    for key in list(os.environ.keys()):
        if key.startswith("SALESFORCE_") and key not in {
            "SALESFORCE_BATTLE_CARD_FIELD",
            "SALESFORCE_SUMMARY_FIELD",
            "SALESFORCE_AUTH_BASE_URL",
            "SALESFORCE_API_VERSION",
        }:
            monkeypatch.delenv(key, raising=False)
