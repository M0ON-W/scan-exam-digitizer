# Provenance and verification record

This file records how the 1.1.0 release tree was assembled. It is an evidence record and does not assert publisher identity or third-party review approval.

## Baseline source

- Input archive: `/mnt/c/Users/WangYue/Downloads/scan-exam-digitizer.zip`
- Expected SHA-256: `2416082584a96362e92bdccede2c110df51ffc0ec14c323ed73a9744b115a982`
- Observed SHA-256 during packaging: `2416082584a96362e92bdccede2c110df51ffc0ec14c323ed73a9744b115a982`
- Archive members: 26 total, including directory entries; 21 regular files copied.
- Baseline source tree destination: `skills/scan-exam-digitizer/`
- Extraction: standard-library ZIP reader after hash, corruption, root-prefix, traversal, duplicate, and symlink checks. The complete source tree is preserved byte-for-byte except for one documented public-submission metadata normalization in `agents/openai.yaml`: legacy `chatgpt`, `codex`, `api`, and `atlas` product tokens were normalized to the current `CHAT` and `CODEX` values. No source `SKILL.md`, workflow, script, reference, asset, or requirements content was rewritten.

## 1.1.0 construction and source-to-release comparison

- The 1.1.0 skill tree is based on the canonical working copy at `C:\Users\WangYue\.codex\skills\scan-exam-digitizer` and is synchronized to five additional active/runtime/publication copies, including `C:\Users\WangYue\.gemini\config\skills\scan-exam-digitizer`.
- Deliberate 1.1.0 changes are limited to the skill contract, references, LaTeX layout helpers, validator/inspection scripts, layout linter, and regression tests. They add semantic-before-redraw and measurable layout gates; they do not replace the original scan as the factual source.
- `SOURCE_VS_RELEASE.diff` summarizes the baseline-to-1.1.0 changes, including the new schema `1.2` and layout evidence requirements. The original archive SHA-256 remains recorded as the immutable baseline, not as a claim that the modified 1.1.0 tree is byte-identical to that archive.
- The plugin root additionally contains the package-level 48×48 SVG listing assets, `assets/logo.svg` and `assets/composer-icon.svg`, referenced by the plugin manifest.
- Remote publication must use `remote_additive_tree_sha256` together with the recorded `remote_preserved_file_sha256` values. The local candidate's `README.md` and `LICENSE` are not authoritative for that remote write because the user created different files in the existing repository.
- The package-specific release tree hash and shared release-set hash are in `RELEASE_HASH.json`; the marker itself is excluded from the tree-hash scope.

## Release metadata

- Plugin name: `scan-exam-digitizer`
- Version: `1.1.0`
- License field: `MIT`
- Intended repository: `https://github.com/M0ON-W/scan-exam-digitizer`
- Apps/MCP declarations: none
- Listing assets: `assets/logo.svg`, `assets/composer-icon.svg`
- Publisher identity: `UNVERIFIED — explicit user confirmation required`

## Verification record

- `python3 -m unittest discover -s skills/scan-exam-digitizer/tests -p 'test_*.py'`: 25 tests passed in the canonical tree; the same suite passed independently in all five synchronized copies.
- `python3 /mnt/c/Users/WangYue/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/scan-exam-digitizer`: passed.
- The circuit/table fixture compiled with WSL XeLaTeX, retained an extractable PDF text layer, rendered to one PNG page, and passed a visual inspection for readable spacing, no clipping, and balanced scale.
- The Windows Tectonic executable at `D:\Gemini\模拟电子电路总复习\.agents\skills\tools\tectonic\tectonic.exe` resolves and reports `0.15.0`; direct compilation is not marked as passed because cached dependencies and the required CJK font are unavailable in that runtime.

## Local old-version enumeration

- `/mnt/c/Users/WangYue/.codex/skills/scan-exam-digitizer`: found and left untouched.
- `/mnt/c/Users/WangYue/.codex/plugins/cache/personal/scan-exam-digitizer-chat/1.0.0/skills/scan-exam-digitizer`: found and left untouched.
- No old file was moved, removed, or overwritten by this packaging run.

## Verification boundaries

This record does not prove publisher identity, copyright ownership, OpenAI review approval, Apps Management state, Cloud state, Platform state, or account installation. The GitHub target and final commit/tree checks are verified separately from this provenance record.

## Local VCS

A local release snapshot remains on branch `codex/scan-exam-digitizer-1.0.0-candidate`; the historical branch name is retained for traceability. No publisher identity was invented. The GitHub publication checkout and its direct `main` push are verified independently.
