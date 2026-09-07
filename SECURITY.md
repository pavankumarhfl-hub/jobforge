# Security Policy

**Maintainer:** Pavan Kumar BN

JobForge is a queue library, not a sandbox. It does not execute job payloads and should not be treated as a security boundary.

## Reporting a vulnerability

Please avoid publishing sensitive vulnerability details in a public issue. Use GitHub's private security reporting features when available.

## Safe usage

- Validate untrusted job payloads before execution.
- Apply authorization at the worker/application layer.
- Do not store credentials unnecessarily in queue payloads.
- Restrict access to the SQLite database file.
- Define retention policies for sensitive job data.
