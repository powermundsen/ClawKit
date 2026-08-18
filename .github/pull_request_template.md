## What and why

Describe the user need and classify the change as core, optional module, or personal instance behavior.

## Data flow and permissions

Describe new reads, writes, network calls, external recipients, and approval points. Write `none` where applicable.

## Verification

- [ ] Tests use temporary, synthetic data
- [ ] `python installer/privacy-scan.py` passes
- [ ] Relevant docs and changelog are updated
- [ ] No secrets, conversations, health exports, memories, logs, or absolute personal paths are included
- [ ] No pay-per-call API is required
- [ ] Migration and rollback impact is documented

