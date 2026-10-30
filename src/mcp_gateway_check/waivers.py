"""Waiver files: TOML records that accept a finding for a reason until a date."""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from .checks import Finding, finding
from .model import InputError
from .rules import RULES

MAX_DAYS = 180  # CONF-2


@dataclass
class Waiver:
    rule: str
    target: str
    reason: str
    owner: str
    expires: dt.date
    used: int = 0

    def matches(self, f: Finding) -> bool:
        if not fnmatchcase(f.rule, self.rule):
            return False
        candidates = {f.target}
        if f.group:
            candidates.add(f.group)
        if f.tool:
            candidates.add(f.tool)
        return any(fnmatchcase(c, self.target) for c in candidates)


def load_waivers(path: Path, today: dt.date) -> list[Waiver]:
    """Parse a waiver file. Missing fields, unknown rules, or long expiries are input errors."""
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc
    entries = doc.get("waiver", [])
    if not isinstance(entries, list):
        raise InputError(f"{path}: use [[waiver]] tables")
    out = []
    for i, w in enumerate(entries, 1):
        where = f"{path} waiver #{i}"
        for key in ("rule", "target", "reason", "owner", "expires"):
            if key not in w or (isinstance(w[key], str) and not w[key].strip()):
                raise InputError(f"{where}: missing {key!r} (CONF-2)")
        expires = w["expires"]
        if isinstance(expires, dt.datetime):
            expires = expires.date()
        if not isinstance(expires, dt.date):
            raise InputError(f"{where}: expires must be a TOML date like 2027-01-31")
        if not any(fnmatchcase(r, w["rule"]) for r in RULES):
            raise InputError(f"{where}: rule {w['rule']!r} matches no rule ID")
        if (expires - today).days > MAX_DAYS:
            raise InputError(f"{where}: expires more than {MAX_DAYS} days from today (CONF-2)")
        out.append(Waiver(w["rule"], w["target"], w["reason"].strip(), w["owner"].strip(), expires))
    return out


def apply_waivers(findings: list[Finding], waivers: list[Waiver], today: dt.date) -> list[Finding]:
    """Mark waived findings and add CONF-3 findings for expired or unused waivers."""
    active = [w for w in waivers if w.expires >= today]
    for f in findings:
        for w in active:
            if w.matches(f):
                f.waived = True
                f.waiver_reason = f"{w.reason} (owner {w.owner}, expires {w.expires})"
                w.used += 1
                break
    extra = []
    for w in waivers:
        if w.expires < today:
            extra.append(
                finding(
                    "CONF-3",
                    f"waiver for {w.rule} on {w.target!r} expired {w.expires}; findings are active again",
                    group=w.target,
                )
            )
        elif w.used == 0:
            extra.append(finding("CONF-3", f"waiver for {w.rule} on {w.target!r} matched nothing", group=w.target))
    return findings + extra
