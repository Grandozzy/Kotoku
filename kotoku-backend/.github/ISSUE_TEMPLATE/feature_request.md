---
name: Feature request
about: Propose a new capability or workflow improvement
title: "[Feature] "
labels: ["enhancement"]
assignees: []
---

## Summary

- What capability is needed?
- Why does it matter?

## Proposed Scope

- Owning app or domain:
- API changes:
- Model changes:
- Async work needed:
- External integrations needed:

## Architecture Notes

- Write workflows should live in `services.py`.
- Read/query workflows should live in `selectors.py`.
- Views should stay thin.
- Domain-owned tasks should stay in the owning app.
- Important write paths should emit audit events.

## Acceptance Criteria

- [ ] 
- [ ] 
- [ ] 

## Testing Notes

- Unit tests needed:
- Integration tests needed:
- E2E coverage needed:

## Documentation Notes

- Which files in `docs/` should change?

Follow the project structure and architecture rules in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
