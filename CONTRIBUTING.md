# Contributing

Changes fall into four kinds: rules, profiles, checker code, and docs.

## Ground rules

- Every rule change cites evidence. Opinions without a source are not enough.
- Keep the spec product-neutral. Product details go in [profiles/](profiles/).
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Read [docs/versioning.md](docs/versioning.md) first if your change adds, removes, or changes the level of a rule.

## Propose a rule

Open a [rule proposal](https://github.com/justcarlson/mcp-gateway-spec/issues/new?template=rule-proposal.yml) before the pull request. It needs:

1. **The problem.** What goes wrong without the rule, with a real example. Anonymize hostnames, accounts, and private names.
2. **Evidence, with a citation.** At least one of: the MCP specification or a SEP, client documentation, a published measurement, or a public gateway's code or docs. Link the exact page or line, and give the date you checked it.
3. **The rule text**, with a level (MUST, SHOULD, MAY) and a one-line reason.
4. **The MCP revisions** it applies to (`since`, and `until` if it ends).
5. **How to test it.** Can the checker test it from a dump, or is it a review item?

In the pull request:

- Add the rule to the right section of [SPEC.md](SPEC.md) in the same format as its neighbors. Add new sources to section 18 with a "verified on" date.
- Add it to `src/mcp_gateway_check/rules.py` with the same level and window. The tests fail if SPEC.md and the registry disagree.
- Regenerate the rule index table in SPEC.md section 17 (the test prints the expected rows).
- If the checker tests it, add a check in `checks.py`, a bad fixture in `tests/fixtures/bad/`, and a manifest entry.
- Add a CHANGELOG entry. A new MUST is **Breaking**.

Rule IDs never change meaning and are never reused.

## Add a profile

A profile maps the spec onto one gateway product. Copy the shape of [profiles/flat-proxy.md](profiles/flat-proxy.md):

1. A mapping table from spec terms (group, view, meta-tool, approval, edge) to the product's terms, with links to its docs.
2. The product settings that satisfy each rule family, and the rules it cannot meet.
3. How to run the checker on it: the dump command or endpoint, and the `--namespace` and `--discovery` flags.
4. A checker run on a real or sample dump. Do not commit private dumps.

Do not write that a product "conforms". Conformance belongs to a specific view, with a report.

## Checker changes

- Python 3.12 or later, standard library only.
- Run the tests and linters before you push:

  ```sh
  PYTHONPATH=src python3 -m unittest discover -s tests
  python3 scripts/lint_fixtures.py
  python3 scripts/conformance.py --check
  uvx ruff check src tests scripts && uvx ruff format --check src tests scripts
  ```

- Never accept a token on the command line. Read secrets from the environment.

## MCP revisions

Do not edit `upstream.json` by hand for a new revision without a tracking issue. The daily workflow opens one. Follow [docs/versioning.md](docs/versioning.md#release-policy).

## Commit and pull request

- One topic per pull request. Fill in the template.
- For changes to gateway surfaces in examples or templates, run the checker and paste the result.
