#!/usr/bin/env python3
"""Migrate obsidian-wiki vault pages from native frontmatter to OKF v0.2.

Converts:
  category: concepts  →  type: Concept
  summary: ...        →  description: ...
  updated: <ISO>      →  generated: {by, at}
  timestamp: <ISO>    →  generated: {by, at}  (if both present, generated wins)

Usage:
  python3 scripts/migrate-okf.py /path/to/vault [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_SKIP_DIRS = frozenset(
    "_raw _archived _staging _archives _bootstrap .obsidian .git node_modules __pycache__ .venv venv".split()
)

# OKF type mapping: old category values → new type values
_CATEGORY_TO_TYPE: dict[str, str] = {
    "concepts": "Concept",
    "entities": "Entity",
    "skills": "Skill",
    "references": "Reference",
    "synthesis": "Synthesis",
    "projects": "Project",
    "journal": "Journal",
}


def _iter_pages(vault: Path) -> list[Path]:
    return [
        path for path in vault.rglob("*.md")
        if not any(part in _SKIP_DIRS for part in path.relative_to(vault).parts)
    ]


def _migrate_frontmatter(text: str, *, dry_run: bool) -> tuple[str, list[str]]:
    """Migrate one file's frontmatter to OKF v0.2. Returns (new_text, changes)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return text, []

    front = match.group(1)
    changes: list[str] = []
    lines = front.splitlines()
    output: list[str] = []
    in_block: str | None = None  # track block scalars (>, |) or YAML objects
    block_lines: list[str] = []

    # Phase 1: collect field changes
    has_type = False
    has_description = False
    has_generated = False
    has_updated = False
    has_timestamp = False
    has_category = False
    has_summary = False
    has_created = False
    has_status = False

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 0:
            if stripped.startswith("category:"):
                has_category = True
                cat_val = stripped.split(":", 1)[1].strip().strip("'\"")
            elif stripped.startswith("type:"):
                has_type = True
            elif stripped.startswith("description:"):
                has_description = True
            elif stripped.startswith("summary:"):
                has_summary = True
            elif stripped.startswith("generated:"):
                has_generated = True
            elif stripped.startswith("updated:"):
                has_updated = True
            elif stripped.startswith("timestamp:"):
                has_timestamp = True
            elif stripped.startswith("created:"):
                has_created = True
            elif stripped.startswith("status:"):
                has_status = True

    # Phase 2: rewrite lines
    _needs_generated_fallback = False
    _updated_value: str | None = None
    _timestamp_value: str | None = None
    _cat_value: str | None = None
    _summary_value: str | None = None

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Track block content (inside | or > scalars, or YAML objects)
        if indent > 0 and in_block:
            block_lines.append(line)
            continue
        if in_block:
            # End of block scalar
            block_text = "\n".join(block_lines)
            output.append(block_text)
            block_lines = []
            in_block = None

        if indent == 0:
            if stripped.startswith("category:") and not has_type:
                _cat_value = stripped.split(":", 1)[1].strip().strip("'\"")
                new_type = _CATEGORY_TO_TYPE.get(_cat_value, "")
                if new_type:
                    output.append(f"type: {new_type}")
                    changes.append(f"category → type: {new_type}")
                    continue
                else:
                    # Unknown category — change anyway with same value
                    output.append(f"type: {_cat_value}")
                    changes.append(f"category → type: {_cat_value}")
                    continue

            if stripped.startswith("summary:") and not has_description:
                val = stripped.split(":", 1)[1].strip()
                output.append(f"description:{' ' + val if val else ''}")
                changes.append("summary → description")
                if ">" in val:
                    in_block = "description"
                continue

            if stripped.startswith("updated:") and not has_generated:
                _updated_value = stripped.split(":", 1)[1].strip().strip("'\"")
                output.append(stripped)  # keep as-is during scan, will remove later
                has_updated = True  # signal that we found a value
                continue

            if stripped.startswith("timestamp:") and not has_generated and not has_updated:
                _timestamp_value = stripped.split(":", 1)[1].strip().strip("'\"")
                has_timestamp = True

        output.append(line)

    if block_lines:
        output.append("\n".join(block_lines))

    # Phase 3: handle generated replacement
    if not has_generated and (_updated_value or _timestamp_value):
        ts = _timestamp_value or _updated_value or datetime.now(timezone.utc).isoformat()
        generated_block = (
            f"generated:\n"
            f"  by: \"migrate-okf-script/hermes\"\n"
            f"  at: {ts}"
        )
        # Insert generated after the line that had updated/timestamp, or at end
        # Find the last position of updated: or timestamp: line
        insert_pos = -1
        for idx, line in enumerate(output):
            if line.startswith("updated:") or line.startswith("timestamp:"):
                insert_pos = idx

        if insert_pos >= 0:
            output[insert_pos] = generated_block
        else:
            # Append to frontmatter
            output.append(generated_block)

        # Remove the other timestamp field
        if _updated_value and has_updated:
            output = [l for l in output if not l.startswith("updated:") and not l.startswith("timestamp:")]
            output.insert(output.index(generated_block) + 1 if generated_block in output else -1, generated_block)

        changes.append(f"updated/timestamp → generated (at: {ts})")

    # Phase 4: add generated if absent entirely
    if not has_generated and not _updated_value and not has_timestamp and has_created:
        # Derive generated from created
        output.append(f"\ngenerated:\n  by: \"migrate-okf-script/hermes\"\n  at: <created-value>")

    result = "\n".join(output)
    new_text = "---\n" + result + "\n---\n" + text[match.end():]
    return new_text, changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate vault pages to OKF v0.2 frontmatter")
    parser.add_argument("vault", type=str, help="Path to the Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without modifying files")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"Error: vault directory not found: {vault}", file=sys.stderr)
        sys.exit(1)

    pages = _iter_pages(vault)
    total_changes = 0
    changed_files: list[str] = []
    unchanged_files: list[str] = []

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        new_text, changes = _migrate_frontmatter(text, dry_run=args.dry_run)
        if changes:
            total_changes += len(changes)
            changed_files.append(str(page.relative_to(vault)))
            if not args.dry_run:
                page.write_text(new_text, encoding="utf-8")
        else:
            unchanged_files.append(str(page.relative_to(vault)))

    print(f"Vault: {vault}")
    print(f"Total pages: {len(pages)}")
    print(f"Modified: {len(changed_files)}")
    print(f"Unchanged: {len(unchanged_files)}")
    print(f"Total field changes: {total_changes}")

    if changed_files:
        print(f"\nChanged files ({min(10, len(changed_files))} shown):")
        for f in changed_files[:10]:
            print(f"  + {f}")
        if len(changed_files) > 10:
            print(f"  ... and {len(changed_files) - 10} more")

    if args.dry_run:
        print("\n[Dry run — no files modified]")
        if total_changes == 0:
            print("Already up to date with OKF v0.2")
    else:
        print("\nMigration complete.")
        print("Run 'python3 scripts/migrate-okf.py /path/to/vault --dry-run' to verify first.")


if __name__ == "__main__":
    main()