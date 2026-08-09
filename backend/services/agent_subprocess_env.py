"""Hosted agent subprocess environment hardening (REQ-017 / issue #199).

Clears PYTHONPATH and strips control-plane paths (EVOTOWN_DATA_DIR, MCP dirs)
so Bash inside a coding-agent run cannot casually ``import infra.mcp_registry``.
Does not replace FS isolation — agents can still set PYTHONPATH=/app manually;
pair with mcp_registry mutator trust gates.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

# Dropped even when inheriting the parent environ (CLI path).
_DENY_EXACT = frozenset(
    {
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "EVOTOWN_DATA_DIR",
        "EVOTOWN_AGENTS_DIR",
        "EVOTOWN_WORKSPACES_DIR",
        "EVOTOWN_WORKSPACES_HOST_DIR",
        "MCP_SERVICES_DIR",
        "MCP_DEV_DIR",
        "DATABASE_URL",
    }
)

_DENY_PREFIXES = (
    "ADMIN_",
    "EVOTOWN_DATABASE_MCP_",
    "EVOTOWN_DEV_",
    "EVOTOWN_ENGINE_INGEST_",
)


def _allowed_inherited(key: str) -> bool:
    if key in _DENY_EXACT:
        return False
    if any(key.startswith(p) for p in _DENY_PREFIXES):
        return False
    return True


def build_hosted_agent_env(
    *,
    workspace_root: Path | str,
    run_id: str,
    model: str = "",
    extra: Mapping[str, str] | None = None,
    inherit_parent: bool = False,
) -> dict[str, str]:
    """Build env for Claude SDK/CLI (and similar) agent subprocesses.

    When ``inherit_parent`` is True (CLI), copy a filtered os.environ then overlay.
    When False (SDK), start from ``extra`` only (caller supplies gateway vars).
    Always force ``PYTHONPATH=""`` so a parent merge cannot keep ``/app``.
    """
    env: dict[str, str] = {}
    if inherit_parent:
        env.update({k: v for k, v in os.environ.items() if _allowed_inherited(k)})

    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            if key in _DENY_EXACT or any(key.startswith(p) for p in _DENY_PREFIXES):
                continue
            env[str(key)] = str(value)

    env["PYTHONPATH"] = ""
    env["EVOTOWN_AGENT_RUN_ID"] = str(run_id)
    env["EVOTOWN_WORKSPACE_ROOT"] = str(workspace_root)
    if model:
        env.setdefault("EVOTOWN_CLAUDE_MODEL", str(model))

    # Belt-and-suspenders: never leak data-dir hints into agent Bash.
    for key in _DENY_EXACT:
        if key == "PYTHONPATH":
            continue
        env.pop(key, None)

    return env
