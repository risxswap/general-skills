#!/usr/bin/env python3
"""Check this skill bundle's metadata, portable references and reachability.

Supports inline Markdown file links, not reference-style links or anchors.
Requires PyYAML. This is a structural check, not a behavioral evaluation.
"""

import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import yaml


EXPECTED = {"development-workflow", "java-backend", "frontend-development", "humanizer-zh", "diagnosing-bugs", "code-review", "business-modeling"}
LINK = re.compile(r"\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)\)")


def prose(text):
    """Ignore fenced examples when collecting runtime references."""
    marker = None
    for line in text.splitlines():
        fence = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence:
            current, rest = fence.groups()
            if marker is None:
                marker = current
            elif current[0] == marker[0] and len(current) >= len(marker) and not rest.strip():
                marker = None
            continue
        if marker is None:
            yield line


def validate(root):
    root = Path(root).resolve()
    bundle = root / "skills"
    errors = []
    entries = sorted(bundle.glob("*/SKILL.md"))
    names = {p.parent.name for p in entries}
    if names != EXPECTED:
        errors.append(f"skill set differs: expected {sorted(EXPECTED)}, found {sorted(names)}")
    for entry in entries:
        try:
            match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", entry.read_text(), re.S)
            if not match:
                raise ValueError("missing YAML frontmatter")
            data = yaml.safe_load(match.group(1))
            if not isinstance(data, dict) or data.get("name") != entry.parent.name:
                raise ValueError("name must match skill directory")
            description = data.get("description")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("description must be non-empty text")
            metadata = yaml.safe_load((entry.parent / "agents/openai.yaml").read_text())
            interface = metadata["interface"]
            if not isinstance(interface.get("display_name"), str) or not interface["display_name"].strip():
                raise ValueError("missing display_name")
            short = interface.get("short_description")
            if not isinstance(short, str) or not 25 <= len(short) <= 64:
                raise ValueError("short_description must contain 25–64 characters")
            prompt = interface.get("default_prompt")
            invocation = rf"\${re.escape(entry.parent.name)}(?![a-zA-Z0-9_-])"
            if not isinstance(prompt, str) or not re.search(invocation, prompt):
                raise ValueError("default_prompt must mention its skill")
            if metadata.get("policy", {}).get("allow_implicit_invocation", True) is not True:
                raise ValueError("this bundle requires automatic discovery")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
            errors.append(f"{entry.relative_to(root)}: {exc}")

    graph = {}
    markdown = sorted(root.rglob("*.md"))
    for path in markdown:
        targets = set()
        text = path.read_text()
        if "\ufffd" in text:
            errors.append(f"{path.relative_to(root)}: replacement character")
        for raw in LINK.findall("\n".join(prose(text))):
            url = urlsplit(raw.strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            relative = Path(unquote(url.path))
            target = (path.parent / relative).resolve()
            if relative.is_absolute():
                errors.append(f"{path.relative_to(root)}: non-portable link {raw}")
            if path.is_relative_to(bundle) and not target.is_relative_to(bundle):
                errors.append(f"{path.relative_to(root)}: runtime link escapes skill bundle: {raw}")
            if not target.exists():
                errors.append(f"{path.relative_to(root)}: missing target {raw}")
            targets.add(target)
        graph[path.resolve()] = targets
    for entry in entries:
        skill_root = entry.parent.resolve()
        reached = set()
        pending = [entry.resolve()]
        while pending:
            current = pending.pop()
            if current not in reached:
                reached.add(current)
                pending.extend(
                    target for target in graph.get(current, ())
                    if target.is_relative_to(skill_root)
                )
        for ref in (entry.parent / "references").rglob("*.md"):
            if ref.resolve() not in reached:
                errors.append(f"{ref.relative_to(root)}: unreachable from its own skill entry")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root)
    for error in errors:
        print(error)
    if not errors:
        print("Skill bundle metadata, file links and reference reachability passed.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
