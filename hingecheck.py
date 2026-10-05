#!/usr/bin/env python3
"""Track explicit assumptions and surface downstream records that need rechecking."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

FORMAT = "hingecheck/0.1"
STATUSES = ("declared", "supported", "uncertain", "challenged", "invalidated")
AUTHORITY_KINDS = ("tool-record", "document", "repository", "commit", "specification", "conversation", "other")
DEPENDENT_KINDS = ("claim", "evidence", "classification", "conflict", "hypothesis", "writing-unit", "conclusion", "other")
DEPENDENCY_TYPES = ("requires", "relies-on", "strengthens", "weakens-if-false", "invalid-if-false", "interpretive-context")


class HingecheckError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_project(title: str) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise HingecheckError("title cannot be empty")
    return {
        "format": FORMAT,
        "title": title,
        "created_at": now_utc(),
        "authorities": [],
        "assumptions": [],
    }


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    high = 0
    for item in items:
        value = item.get("id", "")
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            high = max(high, int(value[len(prefix):]))
    return f"{prefix}{high + 1:03d}"


def find_assumption(data: dict[str, Any], assumption_id: str) -> dict[str, Any]:
    for item in data["assumptions"]:
        if item["id"] == assumption_id:
            return item
    raise HingecheckError(f"assumption not found: {assumption_id}")


def authority_ids(data: dict[str, Any]) -> set[str]:
    return {item["id"] for item in data["authorities"]}


def require_authorities(data: dict[str, Any], refs: list[str] | None) -> list[str]:
    refs = list(dict.fromkeys(refs or []))
    known = authority_ids(data)
    missing = [ref for ref in refs if ref not in known]
    if missing:
        raise HingecheckError("unknown authority: " + ", ".join(missing))
    return refs


def add_authority(data: dict[str, Any], aid: str, label: str, location: str, kind: str = "other", note: str = "") -> None:
    aid = aid.strip()
    label = label.strip()
    location = location.strip()
    if not aid or not label or not location:
        raise HingecheckError("authority id, label, and location cannot be empty")
    if kind not in AUTHORITY_KINDS:
        raise HingecheckError(f"invalid authority kind: {kind}")
    if aid in authority_ids(data):
        raise HingecheckError(f"duplicate authority id: {aid}")
    data["authorities"].append({"id": aid, "label": label, "location": location, "kind": kind, "note": note})


def add_assumption(
    data: dict[str, Any],
    text: str,
    status: str = "declared",
    authorities: list[str] | None = None,
    recheck_when: str = "",
    reason: str = "Initial project state.",
) -> str:
    text = text.strip()
    if not text:
        raise HingecheckError("assumption text cannot be empty")
    if status not in STATUSES:
        raise HingecheckError(f"invalid status: {status}")
    refs = require_authorities(data, authorities)
    hid = next_id(data["assumptions"], "H")
    data["assumptions"].append({
        "id": hid,
        "text": text,
        "status": status,
        "authorities": refs,
        "recheck_when": recheck_when,
        "status_history": [{"status": status, "reason": reason, "authorities": refs}],
        "dependents": [],
    })
    return hid


def add_dependent(
    data: dict[str, Any],
    assumption_id: str,
    dependent_id: str,
    kind: str,
    dependency: str,
    note: str = "",
) -> None:
    assumption = find_assumption(data, assumption_id)
    dependent_id = dependent_id.strip()
    if not dependent_id:
        raise HingecheckError("dependent id cannot be empty")
    if kind not in DEPENDENT_KINDS:
        raise HingecheckError(f"invalid dependent kind: {kind}")
    if dependency not in DEPENDENCY_TYPES:
        raise HingecheckError(f"invalid dependency type: {dependency}")
    if any(d["id"] == dependent_id for d in assumption["dependents"]):
        raise HingecheckError(f"{assumption_id}: duplicate dependent id {dependent_id}")
    assumption["dependents"].append({
        "id": dependent_id,
        "kind": kind,
        "dependency": dependency,
        "note": note,
    })


def change_status(
    data: dict[str, Any],
    assumption_id: str,
    status: str,
    reason: str,
    authorities: list[str] | None = None,
) -> None:
    assumption = find_assumption(data, assumption_id)
    if status not in STATUSES:
        raise HingecheckError(f"invalid status: {status}")
    reason = reason.strip()
    if not reason:
        raise HingecheckError("status change requires a reason")
    refs = require_authorities(data, authorities)
    assumption["status"] = status
    assumption["status_history"].append({
        "status": status,
        "reason": reason,
        "authorities": refs,
    })


def impact(data: dict[str, Any], assumption_id: str) -> list[dict[str, Any]]:
    assumption = find_assumption(data, assumption_id)
    return list(assumption["dependents"])


def audit(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for assumption in data["assumptions"]:
        hid = assumption["id"]
        if not assumption["authorities"]:
            findings.append(f"{hid}: assumption has no authority pointer")
        if not assumption["recheck_when"].strip():
            findings.append(f"{hid}: assumption has no recheck condition")
        if assumption["status"] in ("challenged", "invalidated"):
            latest = assumption["status_history"][-1]
            if not latest["reason"].strip():
                findings.append(f"{hid}: {assumption['status']} status has no reason")
        for dep in assumption["dependents"]:
            if not dep["note"].strip():
                findings.append(f"{hid}/{dep['id']}: dependency has no note")
    return findings


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise HingecheckError("unsupported project format")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise HingecheckError("project requires title")
    if not isinstance(data.get("created_at"), str) or not data["created_at"].strip():
        raise HingecheckError("project requires created_at")
    if not isinstance(data.get("authorities"), list) or not isinstance(data.get("assumptions"), list):
        raise HingecheckError("project requires authorities and assumptions lists")

    known: set[str] = set()
    for item in data["authorities"]:
        aid = item.get("id")
        if not isinstance(aid, str) or not aid.strip() or aid in known:
            raise HingecheckError("invalid or duplicate authority id")
        known.add(aid)
        if item.get("kind") not in AUTHORITY_KINDS:
            raise HingecheckError(f"{aid}: invalid authority kind")
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            raise HingecheckError(f"{aid}: authority label cannot be empty")
        if not isinstance(item.get("location"), str) or not item["location"].strip():
            raise HingecheckError(f"{aid}: authority location cannot be empty")

    hids: set[str] = set()
    for assumption in data["assumptions"]:
        hid = assumption.get("id")
        if not isinstance(hid, str) or not hid.strip() or hid in hids:
            raise HingecheckError("invalid or duplicate assumption id")
        hids.add(hid)
        if not isinstance(assumption.get("text"), str) or not assumption["text"].strip():
            raise HingecheckError(f"{hid}: assumption text cannot be empty")
        if assumption.get("status") not in STATUSES:
            raise HingecheckError(f"{hid}: invalid status")
        for ref in assumption.get("authorities", []):
            if ref not in known:
                raise HingecheckError(f"{hid}: unknown authority {ref}")
        if not isinstance(assumption.get("recheck_when"), str):
            raise HingecheckError(f"{hid}: recheck_when must be a string")

        history = assumption.get("status_history")
        if not isinstance(history, list) or not history:
            raise HingecheckError(f"{hid}: status_history cannot be empty")
        if history[-1].get("status") != assumption["status"]:
            raise HingecheckError(f"{hid}: current status does not match latest history")
        for event in history:
            if event.get("status") not in STATUSES:
                raise HingecheckError(f"{hid}: invalid history status")
            if not isinstance(event.get("reason"), str):
                raise HingecheckError(f"{hid}: history reason must be a string")
            for ref in event.get("authorities", []):
                if ref not in known:
                    raise HingecheckError(f"{hid}: history references unknown authority {ref}")

        dependents = assumption.get("dependents")
        if not isinstance(dependents, list):
            raise HingecheckError(f"{hid}: dependents must be a list")
        seen_dep: set[str] = set()
        for dep in dependents:
            did = dep.get("id")
            if not isinstance(did, str) or not did.strip() or did in seen_dep:
                raise HingecheckError(f"{hid}: invalid or duplicate dependent id")
            seen_dep.add(did)
            if dep.get("kind") not in DEPENDENT_KINDS:
                raise HingecheckError(f"{hid}/{did}: invalid dependent kind")
            if dep.get("dependency") not in DEPENDENCY_TYPES:
                raise HingecheckError(f"{hid}/{did}: invalid dependency type")
            if not isinstance(dep.get("note"), str):
                raise HingecheckError(f"{hid}/{did}: note must be a string")


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise HingecheckError(f"project not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HingecheckError(f"invalid JSON: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_impact(data: dict[str, Any], assumption_id: str) -> str:
    assumption = find_assumption(data, assumption_id)
    lines = [
        f"# Hingecheck impact: {assumption_id}",
        "",
        assumption["text"],
        "",
        f"**Status:** {assumption['status']}",
        "",
        "## Recheck set",
        "",
    ]
    if not assumption["dependents"]:
        lines.append("_No dependents recorded._")
    else:
        for dep in assumption["dependents"]:
            lines.append(f"- {dep['id']} · {dep['kind']} · {dep['dependency']}" + (f" — {dep['note']}" if dep["note"] else ""))
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(data: dict[str, Any]) -> str:
    authorities = {a["id"]: a for a in data["authorities"]}
    lines = [
        f"# {data['title']}",
        "",
        f"_Hingecheck format: {FORMAT}_",
        "",
        "> A changed hinge creates a recheck set, not an automatic verdict set.",
        "",
    ]

    for assumption in data["assumptions"]:
        lines += [f"## {assumption['id']} · {assumption['status']}", "", assumption["text"], ""]
        if assumption["recheck_when"]:
            lines += [f"**Recheck when:** {assumption['recheck_when']}", ""]
        if assumption["authorities"]:
            lines += ["**Authority:**"]
            for ref in assumption["authorities"]:
                a = authorities[ref]
                lines.append(f"- {ref}: {a['label']} ({a['location']})")
            lines.append("")

        lines += ["**Status history:**", ""]
        for event in assumption["status_history"]:
            refs = ", ".join(event["authorities"]) if event["authorities"] else "no authority pointer"
            lines.append(f"- {event['status']} · {event['reason']} · {refs}")
        lines.append("")

        lines += ["**Dependents:**", ""]
        if assumption["dependents"]:
            for dep in assumption["dependents"]:
                note = f" — {dep['note']}" if dep["note"] else ""
                lines.append(f"- {dep['id']} · {dep['kind']} · {dep['dependency']}{note}")
        else:
            lines.append("_No dependents recorded._")
        lines.append("")

    lines += ["## Structural audit", ""]
    findings = audit(data)
    lines += [f"- {item}" for item in findings] if findings else ["_No structural audit flags._"]
    return "\n".join(lines).rstrip() + "\n"


def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for index, assumption in enumerate(data["assumptions"], start=1):
        node = f"H{index:03d}"
        label = f"{assumption['id']} · {assumption['status']} · {assumption['text']}".replace('"', "'").replace("\n", " ")
        lines.append(f'  {node}["{label}"]')
        for j, dep in enumerate(assumption["dependents"], start=1):
            dnode = f"D{index:03d}_{j:03d}"
            dlabel = f"{dep['id']} · {dep['kind']}".replace('"', "'")
            lines.append(f'  {node} -->|"{dep["dependency"]}"| {dnode}["{dlabel}"]')
    return "\n".join(lines) + "\n"


def summary(data: dict[str, Any]) -> str:
    deps = sum(len(a["dependents"]) for a in data["assumptions"])
    active = sum(a["status"] in ("challenged", "invalidated") for a in data["assumptions"])
    return f"{data['title']}: {len(data['assumptions'])} assumption(s), {deps} dependent(s), {active} active recheck hinge(s), {len(audit(data))} audit flag(s)"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hingecheck", description="Track assumptions and downstream recheck impact.")
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("new")
    q.add_argument("file")
    q.add_argument("--title", required=True)

    q = sub.add_parser("authority")
    q.add_argument("file")
    q.add_argument("authority_id")
    q.add_argument("--label", required=True)
    q.add_argument("--location", required=True)
    q.add_argument("--kind", choices=AUTHORITY_KINDS, default="other")
    q.add_argument("--note", default="")

    q = sub.add_parser("assumption")
    q.add_argument("file")
    q.add_argument("text")
    q.add_argument("--status", choices=STATUSES, default="declared")
    q.add_argument("--authority", action="append", default=[])
    q.add_argument("--recheck-when", default="")
    q.add_argument("--reason", default="Initial project state.")

    q = sub.add_parser("depend")
    q.add_argument("file")
    q.add_argument("assumption_id")
    q.add_argument("dependent_id")
    q.add_argument("--kind", choices=DEPENDENT_KINDS, required=True)
    q.add_argument("--type", choices=DEPENDENCY_TYPES, required=True)
    q.add_argument("--note", default="")

    q = sub.add_parser("status")
    q.add_argument("file")
    q.add_argument("assumption_id")
    q.add_argument("status", choices=STATUSES)
    q.add_argument("--reason", required=True)
    q.add_argument("--authority", action="append", default=[])

    q = sub.add_parser("impact")
    q.add_argument("file")
    q.add_argument("assumption_id")
    q.add_argument("-o", "--output")

    for name in ("show", "validate", "audit"):
        q = sub.add_parser(name)
        q.add_argument("file")

    for name in ("render", "mermaid"):
        q = sub.add_parser(name)
        q.add_argument("file")
        q.add_argument("-o", "--output")

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "new":
            if Path(args.file).exists():
                raise HingecheckError(f"refusing to overwrite existing file: {args.file}")
            save(args.file, new_project(args.title))
            print(f"created {args.file}")
            return 0

        data = load(args.file)

        if args.command == "authority":
            add_authority(data, args.authority_id, args.label, args.location, args.kind, args.note)
            save(args.file, data)
            print(args.authority_id)
        elif args.command == "assumption":
            hid = add_assumption(data, args.text, args.status, args.authority, args.recheck_when, args.reason)
            save(args.file, data)
            print(hid)
        elif args.command == "depend":
            add_dependent(data, args.assumption_id, args.dependent_id, args.kind, args.type, args.note)
            save(args.file, data)
            print(args.dependent_id)
        elif args.command == "status":
            change_status(data, args.assumption_id, args.status, args.reason, args.authority)
            save(args.file, data)
            print(args.assumption_id)
        elif args.command == "impact":
            output = render_impact(data, args.assumption_id)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        elif args.command == "show":
            print(summary(data))
        elif args.command == "validate":
            print(f"ok: {args.file}")
        elif args.command == "audit":
            findings = audit(data)
            print("\n".join(findings) if findings else "no structural audit flags")
        else:
            output = render_markdown(data) if args.command == "render" else render_mermaid(data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        return 0
    except HingecheckError as exc:
        print(f"hingecheck: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
