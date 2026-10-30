# Change review checklist

Copy into the pull request for any change to tools, groups, descriptions, approvals, views, edge exposure, or deployment ([CHG-6](../SPEC.md#chg-6)). Tick what applies; write "n/a" next to what does not.

## Summary

- Change type: ☐ new tool ☐ rename or removal ☐ description ☐ schema ☐ approval or hints ☐ new group ☐ view ☐ edge ☐ deploy
- Groups and views affected:
- Owner of each affected group:

## Checker

- [ ] `mcp-gateway-check check <after>` output attached; no new errors
- [ ] `mcp-gateway-check diff <before> <after> --aliases aliases.toml` output attached (renames, removals, schema changes)
- [ ] New waivers have a reason, owner, and expiry within 180 days (CONF-2); unused or expired waivers removed (CONF-3)

## Tools and groups

- [ ] Each new tool follows the [tool description template](tool-description.md)
- [ ] Each new group follows the [group template](group.md)
- [ ] Group has 10 tools or fewer, or a filter or split plan (GRP-4)
- [ ] Names specific and distinguishable from the rest of the view (NAME-9)
- [ ] One tool per user goal; fixed call sequences merged (GRP-7)
- [ ] Minimal required inputs; defaults set (SCHEMA-6)
- [ ] Structured results have `outputSchema` and text (SCHEMA-8)
- [ ] Large results paginate or truncate with a hint (SCHEMA-9)
- [ ] Errors return `isError: true` with a fix hint; rate limits include `retry_after_seconds` (SCHEMA-10, SCHEMA-11)

## Renames, removals, and schema changes

- [ ] Every caller listed: adapters, scripts, skills, schedules, saved prompts (CHG-8)
- [ ] Each caller's owner told
- [ ] Old name kept as an alias or deprecated tool for 30 days and one release (CHG-1, CHG-2)
- [ ] Input changes additive; output changes additive (CHG-3, CHG-4)
- [ ] Slug unchanged, or migration plan for accounts, views, and grants (GRP-3)
- [ ] View surface version bumped: major, minor, or patch (CHG-7)

## Approvals and hints

- [ ] Hints reviewed against behavior, not copied from upstream (ANN-3)
- [ ] Every tool not reviewed as read-only requires approval (ANN-4)
- [ ] Approval enforced on direct calls, `call`, `execute`, adapters, and schedules (ANN-5)
- [ ] Each exception recorded in source with reason and reviewer (ANN-7)
- [ ] **Approval loosened?** Sign-off by a reviewer who is not the author: ________ (CHG-9)

## Views and security

- [ ] New groups added to views on purpose, none by default (VIEW-6)
- [ ] View policy filters list, search, describe, call, and execute (VIEW-2)
- [ ] Shared credentials listed (VIEW-10, SEC-5)
- [ ] Lethal-trifecta review for each changed view: private data ☐ untrusted content ☐ outbound ☐ (SEC-1)
- [ ] Cross-app review of new combinations (SEC-2)
- [ ] Upstream metadata changes reviewed before they are served (SEC-3)

## Edge

- [ ] Edge allowlist updated; new tools disabled until reviewed (EDGE-1)
- [ ] Edge metadata synced; `mcp-gateway-check diff --mode sync` clean (EDGE-3)
- [ ] Adapters and the caller map updated (EDGE-5)

## Descriptions

- [ ] Eval or canary task run before and after (CHG-10)

## Deployment

- [ ] Image pinned by digest; lock file updated (DEP-1)
- [ ] No secrets in the diff, image, command lines, or logs (DEP-2, OBS-2)
- [ ] Backup taken before deploy (DEP-3)
- [ ] Health check gates the deploy (DEP-4)
- [ ] Egress allowlist updated for new upstreams (DEP-5)
- [ ] Rollback steps written: previous digest ________ (DEP-7)
- [ ] After deploy: live checker run and canary call passed (DEP-8)
- [ ] `notifications/tools/list_changed` sent, or cache lifetime allows the change (CHG-5)
