---
title: OKF Frontmatter Specification
category: meta
tags: [okf, specification, frontmatter]
created: 2026-08-26
updated: 2026-08-26
---

# OKF Frontmatter Specification (v0.2)

All wiki pages use OKF v0.2 compatible YAML frontmatter.
See https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## Required Fields

```yaml
type: Concept        # REQUIRED: Concept | Entity | Skill | Reference | Synthesis | Project | Journal
title: Page Title    # REQUIRED: Human-readable title
```

## Recommended Fields

```yaml
description: Summary of the page (used in index.md entries)
tags: [tag1, tag2]   # Category tags from taxonomy
generated:           # OKF v0.2 — last content change (replaces timestamp)
  by: "wiki-ingest/hermes"
  at: 2026-08-26T10:30:00Z
resource: https://example.com   # Canonical URI for the underlying asset
```

## Optional Fields (OKF §5)

```yaml
status: draft                # OKF v0.2 lifecycle: stable | deprecated | ...
sources:                     # OKF v0.2 §5.1 — provenance with per-source credibility signals
  - id: my-source            # REQUIRED for each source entry
    resource: https://...    # Optional URI
    title: Source Title      # Optional
    author: team:my-team     # Optional — actor
    last_modified: 2026-...  # Optional
    usage_count: 42          # Optional
verified:                    # OKF v0.2 §5.2 — who verified this concept
  - by: human:someone
    at: 2026-08-26T10:30:00Z
stale_after: 2026-12-31T00:00:00Z  # OKF v0.2 §5.5 — expiry
aliases: [alt-name]          # Alternative page names for wikilink resolution
```

## Extension Fields (OKF §4.1)

These are not part of OKF core spec but are preserved verbatim in round-trips:

```yaml
# Page creation (independent of last content change)
created: 2026-08-26T10:30:00Z

# Typed relationships to other pages
relationships:
  - target: "[[concepts/foo]]"
    type: extends

# Trust system (obsidian-wiki native)
base_confidence: 0.65        # [0.0, 1.0]
lifecycle: draft             # draft | reviewed | verified | disputed | archived
lifecycle_changed: 2026-08-26
tier: supporting             # core | supporting | peripheral

# Claim provenance fractions
provenance:
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
```

## Type ↔ Directory Mapping

| type | directory |
|------|-----------|
| `Concept` | `concepts/` |
| `Entity` | `entities/` |
| `Skill` | `skills/` |
| `Reference` | `references/` |
| `Synthesis` | `synthesis/` |
| `Project` | `projects/<name>/` |
| `Journal` | `journal/` |

## Legacy Bridge (Phase 1 – Dual Support)

During migration, deprecated fields are accepted with lint warnings:

| Deprecated (v0.1 / native) | OKF v0.2 replacement | Notes |
|---|---|---|
| `category: concepts` | `type: Concept` | Both; new pages must use `type` |
| `summary:` | `description:` | Both; new pages should use `description` |
| `updated: <ISO>` | `generated: {by, at}` | Fallback: lint accepts `updated` |
| `timestamp: <ISO>` | `generated: {by, at}` | v0.1 field, also fallback |
| `sources: [strings]` | `sources: [{id, ...}]` | Flat string list treated as `id` shorthand |
