# Security Policy

## Supported versions

Security fixes are developed against the latest commit on `main` and the latest published release of this public projection.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories:

https://github.com/Seemorghdev/edge-evidence-processor-public/security/advisories/new

Do not open a public issue for an undisclosed vulnerability. A useful report includes:

- the affected version or commit;
- the expected and observed behavior;
- a minimal reproduction using synthetic data only;
- the security impact and affected trust boundary;
- any proposed mitigation or workaround.

Do not include credentials, private evidence, production database contents, or provider account details.

The maintainer aims to acknowledge a complete report within three business days, provide an initial triage decision within seven business days, and coordinate disclosure after a fix or documented mitigation is available.

## Security-relevant scope

Examples include unauthorized mutation of SQLite authority, digest or lineage bypass, path traversal, unsafe handling of manifests or spool paths, container privilege issues, command injection, dependency vulnerabilities with a demonstrated impact, and Terraform examples that could unexpectedly create or expose resources.

The synthetic demos, optional read-only ADK adapter, and sanitized Terraform examples are not claims of production hardening. Reports should identify a concrete security impact rather than a missing production feature.
