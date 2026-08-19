# Dependency capability contract

`assets/dependencies.json` is the machine-readable dependency contract for the deterministic reconstruction workflow. It declares controlled `kind: scan-exam-digitizer-dependency-map` and schema `1.0`. Run `scripts/check_dependencies.py` before selecting an editable reconstruction path; it only reports state and never installs software.

## Capability groups

| Capability | Checked dependencies | If unavailable |
| --- | --- | --- |
| `base` | Pillow, pypdf, a Unicode LaTeX engine, `pdftoppm`, Fontconfig with a visible CJK family, and all Unicode/math/layout packages used by the supplied template | `BLOCKED`; stop reconstruction rather than fabricate an editable result. |
| `table` | `array.sty`, `booktabs.sty`, `longtable.sty`, `multirow.sty` | Use a traceable source crop for the table. Install the TeX `longtable`/tools bundle and `multirow` package before rechecking. |
| `block-diagram` | `tikz.sty` | Use a traceable source crop for the block diagram. |
| `signal-flow` | `tikz.sty` | Use a traceable source crop for the signal-flow diagram. |
| `circuit` | `tikz.sty`, `circuitikz.sty` | Use a traceable source crop for the circuit diagram. |
| `plot-waveform` | `tikz.sty`, `pgfplots.sty` | Use a traceable source crop for the plot or waveform. |

The checker returns `0` and `PASS` when every requested capability is available, `1` and `DEGRADED` when only degradable requested capabilities are unavailable, and `2` and `BLOCKED` when `base` or another non-degradable capability is unavailable. Conditional capabilities depend on `base`, so a missing base dependency is always blocking.

## Usage

```bash
python3 scripts/check_dependencies.py --capability base --capability table --output audit/dependencies.json
```

The JSON report declares `kind: scan-exam-digitizer-dependency-report`, schema `1.0`, and `dependency_map_sha256` for the bundled contract. It names every probed requirement, records its installation hint and the map's type-specific declaration (`import_name`, `package`, or `candidates`), and lists the unavailable degradable capabilities in `fallback_capabilities`. A failed probe has `evidence: null` and a non-empty note; a passing probe has evidence and an empty note. A `PASS` report verifies that Fontconfig can discover a CJK family; the preflight smoke test remains responsible for the content-specific compile, render, and text-layer checks.

This binding proves that recorded fallback evidence is internally consistent with this checked-in dependency contract. It does not make the report unforgeable or prove a human/operator claim about the runtime environment; keep the required fresh visual QA and installation/recheck audit trail.
