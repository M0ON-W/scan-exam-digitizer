# Provenance and verification record

This file records how the local release candidate was assembled. It is an evidence record, not a public-release claim.

## Source

- Input archive: `/mnt/c/Users/WangYue/Downloads/scan-exam-digitizer.zip`
- Expected SHA-256: `2416082584a96362e92bdccede2c110df51ffc0ec14c323ed73a9744b115a982`
- Observed SHA-256 during packaging: `2416082584a96362e92bdccede2c110df51ffc0ec14c323ed73a9744b115a982`
- Archive members: 26 total, including directory entries; 21 regular files copied.
- Source tree destination: `skills/scan-exam-digitizer/`
- Extraction: standard-library ZIP reader after hash, corruption, root-prefix, traversal, duplicate, and symlink checks. The complete source tree is preserved byte-for-byte except for one documented public-submission metadata normalization in `agents/openai.yaml`: legacy `chatgpt`, `codex`, `api`, and `atlas` product tokens were normalized to the current `CHAT` and `CODEX` values. No source `SKILL.md`, workflow, script, reference, asset, or requirements content was rewritten.

## Source-to-release comparison

- Every regular file under `skills/scan-exam-digitizer/` matches the corresponding file in the hash-verified source archive except the documented `agents/openai.yaml` metadata normalization.
- `SOURCE_VS_RELEASE.diff` records the complete, metadata-only source-to-release difference.
- The plugin root additionally contains two new 48×48 SVG listing assets, `assets/logo.svg` and `assets/composer-icon.svg`, referenced by the plugin manifest; these are package-level metadata assets and are not part of the source Skill tree.
- Remote publication must use `remote_additive_tree_sha256` together with the recorded `remote_preserved_file_sha256` values. The local candidate's `README.md` and `LICENSE` are not authoritative for that remote write because the user created different files in the existing repository.
- The package-specific release tree hash and shared release-set hash are in `RELEASE_HASH.json`; the marker itself is excluded from the tree-hash scope.

## Candidate metadata

- Plugin name: `scan-exam-digitizer`
- Version: `1.0.0`
- License field: `MIT`
- Intended repository: `https://github.com/M0ON-W/scan-exam-digitizer`
- Apps/MCP declarations: none
- Listing assets: `assets/logo.svg`, `assets/composer-icon.svg`
- Publisher identity: `UNVERIFIED — explicit user confirmation required`

## Local old-version enumeration

- `/mnt/c/Users/WangYue/.codex/skills/scan-exam-digitizer`: found and left untouched.
- `/mnt/c/Users/WangYue/.codex/plugins/cache/personal/scan-exam-digitizer-chat/1.0.0/skills/scan-exam-digitizer`: found and left untouched.
- No old file was moved, removed, or overwritten by this packaging run.

## Boundaries

This candidate does not prove GitHub repository existence, GitHub write access, Apps Management Write, verified identity, Cloud state, Platform state, or public publication. Those facts remain `UNVERIFIED` or `BLOCKED` until checked through an authorized current connection. No repository was created or pushed by this run.

## Local VCS

A local Git repository was initialized on branch `codex/scan-exam-digitizer-1.0.0-candidate` and the candidate files were staged. No commit was created because no Git `user.name` or `user.email` is configured; no identity was invented. No remote is configured.
