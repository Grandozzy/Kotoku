## Summary

- What changed?
- Why was this change needed?

## Implementation Notes

- Owning app/module:
- Write paths added or changed:
- Read/query paths added or changed:
- Async tasks added or changed:
- Audit events added or changed:

## Architecture Checklist

- [ ] The code lives in the correct app and module.
- [ ] Views remain thin and only orchestrate serializer -> service/selector -> response.
- [ ] Writes are implemented in `services.py`.
- [ ] Reads and query logic are implemented in `selectors.py`.
- [ ] Background jobs stay in the owning app's `tasks.py`.
- [ ] Important write paths emit audit events where required.
- [ ] Shared code added to `common/` is truly cross-app and not domain-specific.
- [ ] External integrations live in `infrastructure/`, not in views.

## Testing

- [ ] Added or updated unit tests
- [ ] Added or updated integration tests when needed
- [ ] `make lint` passed
- [ ] `make test` passed

Test notes:

- 

## Docs

- [ ] Updated `docs/` where API, workflow, or policy behavior changed
- [ ] No docs update needed

## Reviewer Focus

- Please review:
- Main risk area:

For project contribution rules, see [`CONTRIBUTING.md`](CONTRIBUTING.md).
