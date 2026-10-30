# Security policy

## Reporting a vulnerability

Report security issues privately through [GitHub private vulnerability reporting](https://github.com/justcarlson/mcp-gateway-spec/security/advisories/new). Do not open a public issue.

Include what you found, how to reproduce it, and the version or commit. You should get a reply within 7 days.

## Scope

- The `mcp-gateway-check` checker, for example a way to make it leak a token, run code, or write outside its output.
- The workflows in `.github/workflows/`.
- A rule in SPEC.md that, if followed, makes a gateway less safe.

A finding in a gateway product belongs with that product's maintainers. A finding in a profile's description of a product belongs here.

## Supported versions

The latest release gets fixes. Older 0.x releases do not.

## Handling secrets

The checker reads bearer tokens and header values from environment variables only, never from the command line, and does not print them. If you find a path that exposes one, report it as above.
