"""Self-standalone guard: the deployed stack and our image builds must reference only CHERT's own
GitHub Container Registry (ghcr.io/chertsa) or locally-built chertiot images — never Docker Hub,
quay.io or gcr.io. Runtime images live in docker-compose.yml (some via _IMAGE vars resolved from
.env.example); build base images live in our Dockerfiles' FROM lines.

Excluded, and tracked separately as known upstream-source builds (rare CI-only rebuilds):
grafana-brand (builds Grafana from git source) and thingsboard-brand/upstream (vendored TB build).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"

# Our own build-time images (image: chertiot/<name>:dev, built from a local build context).
LOCAL_PREFIX = "chertiot/"
ALLOWED_REGISTRY = "ghcr.io/chertsa/"
PLACEHOLDERS = {"BACKLOG"}

# Core Dockerfiles we control and keep standalone (FROM must be ghcr.io/chertsa/*).
CORE_DOCKERFILES = [
    "portal/Dockerfile",
    "docs-site/Dockerfile",
    "lab/notebook/Dockerfile",
    "lab/hub/Dockerfile",
    "nodered-brand/Dockerfile",
    "deploy/caddy/Dockerfile",
]


def _env_vars() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _resolve(ref: str, env: dict[str, str]) -> str:
    """Resolve ${VAR} and ${VAR:-default} against .env.example (best-effort)."""

    def sub(m: re.Match[str]) -> str:
        inner = m.group(1)
        if ":-" in inner:
            name, default = inner.split(":-", 1)
            return env.get(name.strip(), default)
        return env.get(inner.strip(), "")

    for _ in range(3):  # nested ${A:-name:${B}} needs a couple of passes
        new = re.sub(r"\$\{([^}]+)\}", sub, ref)
        if new == ref:
            break
        ref = new
    return ref


def test_compose_runtime_images_are_chert_only() -> None:
    env = _env_vars()
    offenders: list[str] = []
    for raw in re.findall(r"^\s*image:\s*(\S+)", COMPOSE.read_text(), re.MULTILINE):
        resolved = _resolve(raw, env)
        if resolved in PLACEHOLDERS:
            continue
        if resolved.startswith(ALLOWED_REGISTRY) or resolved.startswith(LOCAL_PREFIX):
            continue
        offenders.append(f"{raw} -> {resolved}")
    assert not offenders, "compose references non-CHERT registries:\n" + "\n".join(offenders)


def test_core_dockerfiles_build_from_chert_ghcr() -> None:
    offenders: list[str] = []
    for rel in CORE_DOCKERFILES:
        for m in re.findall(r"^FROM\s+(\S+)", (ROOT / rel).read_text(), re.MULTILINE):
            if m == "scratch" or m.startswith(ALLOWED_REGISTRY):
                continue
            offenders.append(f"{rel}: FROM {m}")
    assert not offenders, "core Dockerfiles have non-CHERT base images:\n" + "\n".join(offenders)
