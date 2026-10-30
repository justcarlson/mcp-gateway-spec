## What and why

<!-- One topic per pull request. Link the issue or tracking issue. -->

## Kind

- [ ] Rule added or changed (evidence and citation in SPEC.md, registry updated, rule index regenerated)
- [ ] Profile
- [ ] Checker
- [ ] Docs only
- [ ] MCP revision update (follows docs/versioning.md)

## Checks

- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests` passes
- [ ] `python3 scripts/conformance.py --check` and `python3 scripts/check_frozen.py` pass
- [ ] CHANGELOG updated, with **Breaking** for a new MUST and an **Upstream** note when revisions change
- [ ] No private hostnames, accounts, tokens, or dumps
