# Release notes — 1.1.0

## Included

- Bumped the Skills-only plugin version to `1.1.0`.
- Made semantic review a required gate before any circuit, table, waveform, or other visual redraw: reopen the question, record the question and asset functions, map meaning-bearing elements, and exclude answer-based inference.
- Added manifest schema `1.2` semantic provenance and a deterministic `scripts/layout_lint.py` contract for text/line collisions, table padding and row height, font size, width ratio, overflow, and clipping.
- Added reusable LaTeX layout helpers and required `audit/layout-lint.json` evidence while retaining source crops, page mappings, comparison evidence, and uncertainty records.
- Added regression fixtures for label/wire collisions, schema `1.2`, portable engine resolution, and a complete 25-test suite covering the digitization and PDF gates.
- Kept the original scan as the sole factual source; no generative redraw or answer-driven completion is introduced.
- Retained the package-level 48×48 SVG `logo` and `composerIcon` listing assets and the Skills-only boundary.

## Verification notes

- The canonical skill and five synchronized copies, including the Antigravity global copy, each pass the same 25-test suite.
- WSL XeLaTeX, PDF rendering, and PDF text extraction pass the offline integration fixtures. The installed Windows Tectonic executable resolves and reports version `0.15.0`; its cached-only run lacks `circuitikz`, and its online run cannot expose the required CJK font through Windows fontconfig, so direct Tectonic compilation is not marked as a pass.
- The official local `plugin-creator` validator still rejects the current `policy.products` field; this known validator/schema mismatch is recorded separately and does not replace the independent skill and package checks.

## Not included

- No Apps, MCP servers, external connectors, hosted services, or account credentials.
- No claim that the publisher identity or copyright holder is verified.

## Remaining gates

1. User confirms the publisher identity and copyright holder.
2. User reviews and approves the draft policy text.
3. An authorized connection with the required verified identity and write capability is available.
4. The target repository is created or otherwise made available, then publication is separately reviewed.
