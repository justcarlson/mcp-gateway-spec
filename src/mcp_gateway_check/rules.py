"""Rule registry. Every rule ID here has a matching heading in SPEC.md."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .revisions import applies

SPEC_URL = "https://github.com/justcarlson/mcp-gateway-spec/blob/main/SPEC.md"
FIRST = "2025-11-25"  # oldest MCP revision any rule in this spec version covers
STATELESS = "2026-07-28"  # sessions and initialize removed; server/discover, ttlMs, cacheScope added


@dataclass(frozen=True)
class Rule:
    id: str
    level: str  # MUST, MUST NOT, SHOULD, SHOULD NOT, MAY
    title: str
    checked: bool = False
    since: str = FIRST  # first MCP revision the rule applies to
    until: str | None = None  # last MCP revision it applies to (inclusive); None = still current

    def applies_to(self, revision: str) -> bool:
        return applies(self.since, self.until, revision)

    @property
    def mandatory(self) -> bool:
        return self.level.startswith("MUST")

    @property
    def url(self) -> str:
        return f"{SPEC_URL}#{self.id.lower()}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "checked": self.checked,
            "since": self.since,
            "until": self.until,
            "url": self.url,
        }


_RULES = [
    # Naming
    Rule("NAME-1", "MUST", "Tool names use 1-128 characters from [A-Za-z0-9_.-]", True),
    Rule("NAME-2", "MUST", "Tool names are unique in a view, ignoring case", True),
    Rule("NAME-3", "SHOULD", "Tool names are snake_case; namespace segments are identifiers", True),
    Rule("NAME-4", "SHOULD", "Tool names put the verb first (verb_noun)", True),
    Rule("NAME-5", "MUST", "Exposed names, with any gateway prefix, are at most 64 characters", True),
    Rule("NAME-6", "SHOULD", "Exposed names are at most 48 characters; tool names at most 32", True),
    Rule("NAME-7", "SHOULD NOT", "Tool names repeat the group slug", True),
    Rule("NAME-8", "SHOULD NOT", "Tool names reuse a meta-tool name", True),
    Rule("NAME-9", "SHOULD", "Tool names are specific and easy to tell apart"),
    Rule("NAME-10", "SHOULD", "Tools have a human-readable title", True),
    # Grouping
    Rule("GRP-1", "MUST", "Every tool belongs to exactly one group with one owner"),
    Rule("GRP-2", "MUST", "Group slugs match ^[a-z][a-z0-9]{1,19}$", True),
    Rule("GRP-3", "MUST", "Group slugs are stable; renames follow change management"),
    Rule("GRP-4", "SHOULD", "Groups have at most 10 tools", True),
    Rule("GRP-5", "SHOULD", "A group covers one domain; every tool fits its description"),
    Rule("GRP-6", "SHOULD", "Each tool has one risk level; reads and writes are separate tools", True),
    Rule("GRP-7", "SHOULD", "Tools that are always chained become one workflow tool"),
    Rule("GRP-8", "SHOULD", "Groups that differ only by instance say so and share a naming pattern"),
    # Descriptions and instructions
    Rule("DESC-1", "MUST", "Every tool has a non-empty description", True),
    Rule("DESC-2", "SHOULD", "Tool descriptions are 80-1,024 characters", True),
    Rule("DESC-3", "MUST", "Tool descriptions are at most 4,096 characters", True),
    Rule("DESC-4", "SHOULD", "The first sentence states verb, object, and scope in at most 160 characters", True),
    Rule("DESC-5", "SHOULD", "Overlapping tools say when to use them and which tool to use instead"),
    Rule("DESC-6", "SHOULD", "Descriptions explain inputs, returns, and limits; complex inputs get examples"),
    Rule("DESC-7", "MUST NOT", "Metadata contains hidden directives, secrets, or private endpoints", True),
    Rule("DESC-8", "MUST NOT", "Text claims safety behavior that the gateway does not enforce", True),
    Rule("DESC-9", "MUST", "Every group has a description that says when to use it", True),
    Rule("DESC-10", "SHOULD", "Group descriptions are at most 300 characters", True),
    Rule("DESC-11", "SHOULD", "Group instructions say how to use the group in at most 2,048 characters", True),
    Rule("DESC-12", "MUST", "Group instructions are at most 4,096 characters", True),
    Rule("DESC-13", "MUST NOT", "Instructions repeat tool descriptions or act as a security control"),
    Rule("DESC-14", "SHOULD", "Long workflow guidance lives in a skill, not in instructions"),
    # Schemas, responses, errors
    Rule("SCHEMA-1", "MUST", "inputSchema is an object schema", True),
    Rule("SCHEMA-2", "SHOULD", "Tools without arguments set additionalProperties to false", True),
    Rule("SCHEMA-3", "SHOULD", "Every input property has a description", True),
    Rule("SCHEMA-4", "SHOULD", "Parameter names are descriptive and use one style per group", True),
    Rule("SCHEMA-5", "SHOULD", "Input schemas are flat and inline, without $ref", True),
    Rule("SCHEMA-6", "SHOULD", "Only true minimum inputs are required; filters and paging have defaults"),
    Rule("SCHEMA-7", "MUST NOT", "Input schemas expose credentials or gateway-injected parameters", True),
    Rule("SCHEMA-8", "SHOULD", "Structured results declare outputSchema and also return text"),
    Rule("SCHEMA-9", "SHOULD", "Responses stay under 10,000 tokens, paginate, and say how to narrow"),
    Rule("SCHEMA-10", "MUST", "Tool failures return isError results with a fix hint"),
    Rule("SCHEMA-11", "SHOULD", "Rate-limit errors include retry_after_seconds"),
    Rule("SCHEMA-12", "SHOULD", "Results carry stable IDs; stateful handles document their lifetime"),
    # Annotations and approvals
    Rule("ANN-1", "SHOULD", "Tools set all four annotation hints explicitly", True),
    Rule("ANN-2", "MUST", "readOnlyHint is true only for tools without side effects", True),
    Rule("ANN-3", "MUST", "The gateway treats upstream hints as untrusted input to its own review"),
    Rule("ANN-4", "MUST", "Tools not reviewed as read-only require approval by default", True),
    Rule("ANN-5", "MUST", "The gateway enforces approval on every call path"),
    Rule("ANN-6", "SHOULD", "Approval prompts show tool, group, account, and arguments"),
    Rule("ANN-7", "MUST", "Every approval exception records a reason and a reviewer"),
    Rule("ANN-8", "SHOULD", "idempotentHint and openWorldHint are accurate"),
    # Discovery
    Rule("DISC-1", "SHOULD", "Flat views have at most 10 tools and 10,000 tokens of definitions", True),
    Rule("DISC-2", "MUST NOT", "Views with more than 50 tools or 25,000 tokens are served flat", True),
    Rule("DISC-3", "MUST", "Progressive mode offers search, describe, and call with exact names"),
    Rule("DISC-4", "MUST", "Search and describe apply view policy before ranking"),
    Rule("DISC-5", "SHOULD", "Views pin at most 5 frequent tools beside the meta-tools"),
    Rule("DISC-6", "MUST", "Code mode runs in a sandbox and applies the same approvals per call"),
    Rule("DISC-7", "SHOULD", "Server instructions name the groups and say when to search"),
    Rule("DISC-8", "SHOULD NOT", "Discovery depends on per-session toggles", since=STATELESS),
    Rule("DISC-9", "SHOULD", "Admins set the discovery mode per view; clients choose within it"),
    Rule(
        "DISC-10", "MUST", "server/discover returns the view's instructions, the same on every request", since=STATELESS
    ),
    Rule(
        "DISC-11",
        "SHOULD",
        "The initialize result returns the view's instructions, the same in every session",
        until=FIRST,
    ),
    # Views, scoping, identity
    Rule("VIEW-1", "MUST", "A URL or a credential selects the view", since=STATELESS),
    Rule("VIEW-2", "MUST", "View policy filters list, search, describe, call, and execute"),
    Rule("VIEW-3", "MUST", "Deny wins over allow"),
    Rule("VIEW-4", "MUST", "Policy fails closed"),
    Rule("VIEW-5", "MUST", "tools/list is deterministic for a given credential", since=STATELESS),
    Rule("VIEW-6", "MUST", "New groups start in no view"),
    Rule("VIEW-7", "SHOULD", "Views are defined as code in one source of truth"),
    Rule("VIEW-8", "SHOULD", "Views follow least privilege and offer a read-only variant"),
    Rule("VIEW-9", "SHOULD", "Per-view overrides are one record per tool"),
    Rule("VIEW-10", "MUST", "A view grants accounts only for its own groups"),
    # Edge exposure
    Rule("EDGE-1", "MUST", "The edge exposes an explicit allowlist; new tools start disabled"),
    Rule("EDGE-2", "MUST", "Edge prefixes are <slug>_ and the result meets the naming rules"),
    Rule("EDGE-3", "MUST", "Edge metadata caches are synced after every upstream change", True),
    Rule("EDGE-4", "MUST", "Edge authentication is separate; tokens are never passed through"),
    Rule("EDGE-5", "SHOULD", "Edge adapters follow this spec and are listed in a caller map"),
    Rule("EDGE-6", "SHOULD", "Unprefixed exposure is used only for tools that MCP Apps call by name"),
    Rule("EDGE-7", "MUST NOT", "The edge auto-approves calls that need upstream approval"),
    # Change management
    Rule("CHG-1", "MUST", "Renamed or removed tools keep an alias for the deprecation window", True),
    Rule("CHG-2", "MUST", "Deprecation windows last at least 30 days and one release"),
    Rule("CHG-3", "MUST", "Input schema changes are additive", True),
    Rule("CHG-4", "SHOULD", "Output schema changes are additive", True),
    Rule("CHG-5", "MUST", "Servers announce list changes"),
    Rule("CHG-6", "MUST", "Surface changes pass the review checklist with a checker report"),
    Rule("CHG-7", "SHOULD", "Each view's surface has a semantic version"),
    Rule("CHG-8", "MUST", "Callers of a tool are inventoried and notified before a rename"),
    Rule("CHG-9", "MUST", "Changes that loosen approval get explicit sign-off", True),
    Rule("CHG-10", "SHOULD", "Description changes are verified with an eval or a canary"),
    Rule("CHG-11", "MUST", "tools/list results set ttlMs and cacheScope", True, since=STATELESS),
    # Deployment and operations
    Rule("DEP-1", "MUST", "Images are pinned by digest and recorded in a lock file"),
    Rule("DEP-2", "MUST", "Secrets live in a secret manager, never in git, images, argv, or logs"),
    Rule("DEP-3", "MUST", "State is backed up before each deploy; restores are tested"),
    Rule("DEP-4", "MUST", "Health checks gate each deploy"),
    Rule("DEP-5", "MUST", "Egress uses an allowlist that fails closed"),
    Rule("DEP-6", "SHOULD", "Image upgrades are manual; config deploys may be automatic behind checks"),
    Rule("DEP-7", "MUST", "Rollback is documented and rehearsed"),
    Rule("DEP-8", "MUST", "Each deploy ends with a live conformance check and a canary call"),
    Rule("DEP-9", "SHOULD", "Code execution has resource limits; large jobs are split"),
    Rule("DEP-10", "SHOULD", "Desired state is code with drift detection"),
    # Observability
    Rule("OBS-1", "MUST", "Every call is logged with identity, view, tool, decision, and outcome"),
    Rule("OBS-2", "MUST NOT", "Logs contain secrets or unredacted payloads"),
    Rule("OBS-3", "SHOULD", "Metrics cover calls, errors, latency, approvals, and denials"),
    Rule("OBS-4", "SHOULD", "A synthetic probe watches each endpoint and alerts on drift"),
    Rule("OBS-5", "SHOULD", "Configuration changes are audited"),
    Rule("OBS-6", "SHOULD", "Trace context propagates to upstreams"),
    # Security
    Rule("SEC-1", "MUST", "Each view is reviewed for the lethal trifecta"),
    Rule("SEC-2", "MUST", "Adding a group to a view triggers a cross-app risk review"),
    Rule("SEC-3", "MUST", "Upstream metadata is untrusted and re-reviewed when it changes"),
    Rule("SEC-4", "MUST NOT", "The gateway passes client tokens to upstreams"),
    Rule("SEC-5", "MUST", "Upstream credentials are least-privilege; shared ones are recorded"),
    Rule("SEC-6", "SHOULD", "Automation and people use separate views"),
    # Conformance
    Rule("CONF-1", "MUST", "Conformance claims name the spec version, level, and evidence"),
    Rule("CONF-2", "MUST", "Waivers name a rule, target, reason, owner, and expiry", True),
    Rule("CONF-3", "SHOULD", "Unused and expired waivers are removed", True),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}

assert len(RULES) == len(_RULES), "duplicate rule ID"
