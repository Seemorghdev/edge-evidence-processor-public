from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = (
    "docs/history/",
    ".travis.yml",
)

PRIVATE_REPO = "Seemorghdev/" + "edge-evidence-processor"
PRIVATE_SOURCE_IDS = (
    "e054060813a997e6" + "c45027d65552fd9e4ee54f74",
    "e5557cc56e36f015" + "3d571386d48fa6b547058c88",
)
FORBIDDEN_PHRASES = (
    "private " + "monorepo",
    "public processor " + "snapshot",
    "export-only " + "prepared review bundle",
)

CREDENTIAL_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
)
SERVICE_ACCOUNT = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.iam\.gserviceaccount\.com")
WIF = re.compile(r"projects/\d+/locations/global/workloadIdentityPools/[A-Za-z0-9._-]+/providers/[A-Za-z0-9._-]+")
REGISTRY = re.compile(r"[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[A-Za-z0-9._/-]+")

ALLOWED_SERVICE_ACCOUNT = "processor@example-project.iam.gserviceaccount.com"
ALLOWED_REGISTRY_PROJECT = "/example-project/"

findings: list[str] = []

for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or ".git" in path.parts:
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(FORBIDDEN_PATHS[0]) or rel == FORBIDDEN_PATHS[1]:
        findings.append(f"forbidden path: {rel}")
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    if re.search(re.escape(PRIVATE_REPO) + r"(?!-public)", text):
        findings.append(f"private canonical repository coordinate: {rel}")
    for source_id in PRIVATE_SOURCE_IDS:
        if source_id in text:
            findings.append(f"private source object identifier: {rel}")
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            findings.append(f"stale provenance phrase: {rel}")
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.search(text):
            findings.append(f"credential/private-key pattern: {rel}")
    if WIF.search(text):
        findings.append(f"WIF provider coordinate: {rel}")
    for match in SERVICE_ACCOUNT.findall(text):
        if match != ALLOWED_SERVICE_ACCOUNT:
            findings.append(f"non-placeholder service account coordinate: {rel}")
    for match in REGISTRY.findall(text):
        if ALLOWED_REGISTRY_PROJECT not in match:
            findings.append(f"non-placeholder private registry coordinate: {rel}")

if findings:
    raise SystemExit("\n".join(findings))

print("Processor public projection validation PASSED.")
