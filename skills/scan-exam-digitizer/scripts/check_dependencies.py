from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPENDENCY_MAP = ROOT / "assets" / "dependencies.json"
DEPENDENCY_MAP_KIND = "scan-exam-digitizer-dependency-map"
DEPENDENCY_REPORT_KIND = "scan-exam-digitizer-dependency-report"
DEPENDENCY_REPORT_SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dependency_map(path: Path) -> dict[str, object]:
    """Load a dependency contract whose root is a JSON object."""
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Dependency map root must be an object: {path}")
    _validate_dependency_map(value)
    return value


def check_python_module(import_name: str) -> dict[str, object]:
    try:
        found = importlib.util.find_spec(import_name) is not None
    except (ImportError, AttributeError, ValueError) as exc:
        return {"status": "FAIL", "import_name": import_name, "evidence": None, "note": str(exc)}
    return {
        "status": "PASS" if found else "FAIL",
        "import_name": import_name,
        "evidence": import_name if found else None,
        "note": "" if found else f"Python module not found: {import_name}",
    }


def check_executable(candidates: list[str]) -> dict[str, object]:
    found = [(candidate, shutil.which(candidate)) for candidate in candidates]
    selected = next(((candidate, path) for candidate, path in found if path), None)
    return {
        "status": "PASS" if selected else "FAIL",
        "candidates": candidates,
        "evidence": {"candidate": selected[0], "path": selected[1]} if selected else None,
        "note": "" if selected else f"No executable found on PATH: {', '.join(candidates)}",
    }


def check_tex_package(package: str, kpsewhich: str | None) -> dict[str, object]:
    if kpsewhich is None:
        return {
            "status": "FAIL",
            "package": package,
            "evidence": None,
            "note": "kpsewhich is not available on PATH.",
        }
    try:
        result = subprocess.run([kpsewhich, package], text=True, capture_output=True, check=False)
    except OSError as exc:
        return {"status": "FAIL", "package": package, "evidence": None, "note": str(exc)}
    located = result.stdout.strip()
    passed = result.returncode == 0 and bool(located)
    return {
        "status": "PASS" if passed else "FAIL",
        "package": package,
        "evidence": located if passed else None,
        "note": "" if passed else (result.stderr.strip() or f"TeX package not found: {package}"),
    }


def _check_cjk_font(candidates: list[str]) -> dict[str, object]:
    executable = check_executable(candidates)
    evidence = executable.get("evidence")
    if executable["status"] != "PASS" or not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str):
        return {
            "status": "FAIL",
            "evidence": None,
            "note": str(executable.get("note", "Fontconfig discovery command is unavailable.")),
        }
    try:
        result = subprocess.run(
            [evidence["path"], "-f", "%{family[0]}\\n", ":lang=zh"], text=True, capture_output=True, check=False
        )
    except OSError as exc:
        return {"status": "FAIL", "evidence": None, "note": str(exc)}
    family = next((line.split(",", 1)[0].strip() for line in result.stdout.splitlines() if line.strip()), "")
    valid_family = bool(family) and not any(character in family for character in "{}\\\r\n")
    if result.returncode != 0 or not valid_family:
        return {
            "status": "FAIL",
            "evidence": None,
            "note": result.stderr.strip() or "No CJK-capable Fontconfig family is installed.",
        }
    return {
        "status": "PASS",
        "evidence": {"candidate": evidence["candidate"], "path": evidence["path"], "family": family},
        "note": "",
    }


def probe_requirement(requirement: dict[str, object]) -> dict[str, object]:
    """Probe one requirement from the dependency map without modifying the environment."""
    requirement_id = str(requirement["id"])
    requirement_type = str(requirement["type"])
    if requirement_type == "python_module":
        result = check_python_module(str(requirement["import_name"]))
    elif requirement_type == "executable":
        candidates = requirement.get("candidates", [])
        if not isinstance(candidates, list) or not all(isinstance(candidate, str) for candidate in candidates):
            result = {"status": "FAIL", "evidence": None, "note": "Executable candidates must be a list of strings."}
        else:
            result = check_executable(candidates)
    elif requirement_type == "tex_package":
        kpsewhich = shutil.which("kpsewhich")
        result = check_tex_package(str(requirement["package"]), kpsewhich)
    elif requirement_type == "cjk_font":
        candidates = requirement.get("candidates", [])
        if not isinstance(candidates, list) or not all(isinstance(candidate, str) for candidate in candidates):
            result = {"status": "FAIL", "evidence": None, "note": "CJK font candidates must be a list of strings."}
        else:
            result = _check_cjk_font(candidates)
    else:
        result = {"status": "FAIL", "evidence": None, "note": f"Unknown requirement type: {requirement_type}"}
    report = {
        "id": requirement_id,
        "type": requirement_type,
        "status": result["status"],
        "evidence": result.get("evidence"),
        "note": result.get("note", ""),
        "installation_hint": requirement.get("installation_hint", ""),
    }
    for field in ("import_name", "package", "candidates"):
        if field in requirement:
            report[field] = requirement[field]
    return report


def _requirements_by_id(dependency_map: dict[str, object]) -> dict[str, dict[str, object]]:
    requirements = dependency_map.get("requirements")
    if isinstance(requirements, dict):
        return {
            str(identifier): value
            for identifier, value in requirements.items()
            if isinstance(value, dict)
        }
    if isinstance(requirements, list):
        return {
            str(requirement["id"]): requirement
            for requirement in requirements
            if isinstance(requirement, dict) and "id" in requirement
        }
    raise ValueError("Dependency map requirements must be an object or list.")


def _validate_dependency_map(dependency_map: dict[str, object]) -> None:
    if dependency_map.get("kind") != DEPENDENCY_MAP_KIND:
        raise ValueError(f"Dependency map kind must be {DEPENDENCY_MAP_KIND!r}.")
    if dependency_map.get("schema_version") != DEPENDENCY_REPORT_SCHEMA_VERSION:
        raise ValueError(f"Dependency map schema_version must be {DEPENDENCY_REPORT_SCHEMA_VERSION!r}.")
    requirements = _requirements_by_id(dependency_map)
    raw_requirements = dependency_map.get("requirements")
    if not isinstance(raw_requirements, (dict, list)) or len(requirements) != len(raw_requirements):
        raise ValueError("Every dependency requirement must be an object with an id.")
    for identifier, requirement in requirements.items():
        if requirement.get("id") != identifier or not isinstance(requirement.get("type"), str):
            raise ValueError(f"Invalid dependency requirement: {identifier}")
        requirement_type = requirement["type"]
        if requirement_type == "python_module" and not isinstance(requirement.get("import_name"), str):
            raise ValueError(f"Python requirement needs import_name: {identifier}")
        if requirement_type == "tex_package" and not isinstance(requirement.get("package"), str):
            raise ValueError(f"TeX requirement needs package: {identifier}")
        if requirement_type in {"executable", "cjk_font"}:
            candidates = requirement.get("candidates")
            if not isinstance(candidates, list) or not candidates or not all(isinstance(candidate, str) for candidate in candidates):
                raise ValueError(f"Executable requirement needs candidates: {identifier}")
        if requirement_type not in {"python_module", "executable", "tex_package", "cjk_font"}:
            raise ValueError(f"Unknown requirement type: {requirement_type}")
    capabilities = dependency_map.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("Dependency map capabilities must be an object.")
    for name, capability in capabilities.items():
        if not isinstance(capability, dict):
            raise ValueError(f"Capability must be an object: {name}")
        for field in ("requirements", "requires"):
            values = capability.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"Capability {field} must be a list of strings: {name}")
        if not isinstance(capability.get("degradable"), bool):
            raise ValueError(f"Capability degradable must be boolean: {name}")
        unknown_requirements = set(capability["requirements"]) - set(requirements)
        if unknown_requirements:
            raise ValueError(f"Capability {name} has unknown requirements: {sorted(unknown_requirements)}")
        unknown_parents = set(capability.get("requires", [])) - set(capabilities)
        if unknown_parents:
            raise ValueError(f"Capability {name} has unknown parents: {sorted(unknown_parents)}")


def evaluate_capabilities(
    dependency_map: dict, requested: set[str], dependency_map_sha256: str | None = None
) -> tuple[int, dict]:
    """Evaluate requested capability groups and return an exit code plus JSON-safe report."""
    capabilities = dependency_map.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("Dependency map capabilities must be an object.")
    requirements = _requirements_by_id(dependency_map)
    requested_names = sorted(requested)
    unknown = [name for name in requested_names if name not in capabilities]
    selected: set[str] = set()

    def select(name: str) -> None:
        if name in selected or name not in capabilities:
            return
        selected.add(name)
        capability = capabilities[name]
        if not isinstance(capability, dict):
            raise ValueError(f"Capability must be an object: {name}")
        parents = capability.get("requires", [])
        if not isinstance(parents, list) or not all(isinstance(parent, str) for parent in parents):
            raise ValueError(f"Capability requires must be a list of strings: {name}")
        for parent in parents:
            if parent not in capabilities:
                raise ValueError(f"Capability {name} requires unknown capability: {parent}")
            select(parent)

    for name in requested_names:
        select(name)

    probe_results: dict[str, dict[str, object]] = {}
    capability_results: dict[str, dict[str, object]] = {}
    fallback_capabilities: list[str] = []
    blocking = bool(unknown)

    for name in sorted(selected):
        capability = capabilities[name]
        if not isinstance(capability, dict):
            raise ValueError(f"Capability must be an object: {name}")
        requirement_ids = capability.get("requirements", [])
        if not isinstance(requirement_ids, list) or not all(isinstance(identifier, str) for identifier in requirement_ids):
            raise ValueError(f"Capability requirements must be a list of strings: {name}")
        missing_ids: list[str] = []
        for requirement_id in requirement_ids:
            requirement = requirements.get(requirement_id)
            if requirement is None:
                missing_ids.append(requirement_id)
                probe_results[requirement_id] = {
                    "id": requirement_id,
                    "status": "FAIL",
                    "evidence": None,
                    "note": "Requirement is absent from the dependency map.",
                    "installation_hint": "",
                }
                continue
            if requirement_id not in probe_results:
                probe_results[requirement_id] = probe_requirement(requirement)
            result = probe_results[requirement_id]
            if result.get("status") != "PASS":
                missing_ids.append(requirement_id)
        passed = not missing_ids
        degradable = bool(capability.get("degradable", False))
        capability_results[name] = {
            "status": "PASS" if passed else "FAIL",
            "requirements": requirement_ids,
            "missing_requirements": missing_ids,
            "degradable": degradable,
            "fallback": capability.get("fallback"),
        }
        if not passed:
            if degradable:
                fallback_capabilities.append(name)
            else:
                blocking = True

    if blocking:
        status, exit_code = "BLOCKED", 2
    elif fallback_capabilities:
        status, exit_code = "DEGRADED", 1
    else:
        status, exit_code = "PASS", 0
    return exit_code, {
        "kind": DEPENDENCY_REPORT_KIND,
        "schema_version": DEPENDENCY_REPORT_SCHEMA_VERSION,
        "dependency_map_sha256": dependency_map_sha256 or sha256_file(DEFAULT_DEPENDENCY_MAP),
        "status": status,
        "requested_capabilities": requested_names,
        "capabilities": capability_results,
        "requirements": probe_results,
        "unknown_capabilities": unknown,
        "fallback_capabilities": fallback_capabilities,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report scan-exam digitizer dependency capabilities as JSON.")
    parser.add_argument("--capability", action="append", required=True, help="Capability group to evaluate; may be repeated.")
    parser.add_argument("--output", type=Path, help="Optional JSON report path; otherwise write to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dependency_map = load_dependency_map(DEFAULT_DEPENDENCY_MAP)
        exit_code, report = evaluate_capabilities(
            dependency_map, set(args.capability), dependency_map_sha256=sha256_file(DEFAULT_DEPENDENCY_MAP)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        exit_code = 2
        report = {"schema_version": None, "status": "BLOCKED", "error": str(exc)}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        except OSError as exc:
            error_report = {
                "schema_version": report.get("schema_version"),
                "status": "BLOCKED",
                "error": f"Cannot write output {args.output}: {exc}",
            }
            sys.stdout.write(json.dumps(error_report, ensure_ascii=False, indent=2) + "\n")
            return 2
    else:
        sys.stdout.write(payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
