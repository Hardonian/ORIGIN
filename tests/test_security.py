"""Security / hardening tests.

These assert *properties of the source tree*, not runtime behaviour: that we do
not commit secrets, do not use unsafe deserialization, and do not expose
network services beyond loopback by default.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "packages" / "origin"

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"']"),
    re.compile(r"(?i)secret\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"']"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def _python_files():
    return list(PKG.rglob("*.py"))


def test_no_hardcoded_secrets_in_source():
    offenders = []
    for p in _python_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                offenders.append((str(p.relative_to(REPO)), pat.pattern))
    assert not offenders, f"possible hardcoded secrets: {offenders}"


def test_no_pickle_or_unsafe_deserialization():
    offenders = []
    for p in _python_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bimport\s+pickle\b", text) or re.search(r"\bpickle\.loads?\b", text):
            offenders.append(str(p.relative_to(REPO)))
        if "yaml.load(" in text and "SafeLoader" not in text:
            offenders.append(str(p.relative_to(REPO)))
    assert not offenders, f"unsafe deserialization in: {offenders}"


def test_api_binds_loopback_by_default():
    text = (PKG / "experiments" / "api.py").read_text()
    assert 'default="127.0.0.1"' in text, "API must default to loopback"


def test_api_enforces_auth_on_external_interface():
    text = (PKG / "experiments" / "api.py").read_text()
    assert "secrets.token_hex" in text, "API must generate or require a token for external binding"
    assert "ORIGIN_API_KEY" in text, "API must support ORIGIN_API_KEY environment variable"
    assert "compare_digest" in text, "API must use constant-time digest comparison"


def test_no_shell_true_or_eval_of_user_input():
    offenders = []
    for p in _python_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "shell=True" in text:
            offenders.append(str(p.relative_to(REPO)))
        if re.search(r"\beval\(", text) or re.search(r"\bexec\(", text):
            offenders.append(str(p.relative_to(REPO)))
    assert not offenders, f"unsafe execution in: {offenders}"


def test_ci_workflow_has_no_plaintext_secrets():
    ci = REPO / ".github" / "workflows" / "ci.yml"
    if ci.exists():
        text = ci.read_text()
        # secrets must be referenced via ${{ secrets.* }}, never inlined
        assert not re.search(r"[\"'](ghp_|sk-|AKIA)", text)
