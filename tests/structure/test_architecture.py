"""
tests/structure/test_architecture.py — the layer rule, enforced mechanically.

    core.allocation  ->  core  ->  modules  ->  api
    (pure domain)        (infra)   (services)   (HTTP)

Imports may only point LEFT. A failure message says what to move and where, because
the message is what the next person (or coding agent) reads. See ARCHITECTURE.md#layers.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# layer -> packages it must never import
FORBIDDEN = {
    "core": ("modules", "api"),
    "modules": ("api",),
    "loaders": ("api",),
}

# Third-party / infrastructure roots the pure domain package may not touch.
PURE_PACKAGE = ROOT / "core" / "allocation"
STDLIB = set(sys.stdlib_module_names)


def _python_files(folder: Path):
    return [p for p in folder.rglob("*.py") if "__pycache__" not in p.parts]


def _imports(path: Path):
    """Yield (line, top-level module, full module, relative level) for every import in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0], alias.name, 0
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            yield node.lineno, module.split(".")[0], module, node.level


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layers_only_import_leftwards(layer):
    violations = []
    for path in _python_files(ROOT / layer):
        for line, top, full, level in _imports(path):
            if level == 0 and top in FORBIDDEN[layer]:
                violations.append(
                    f"{path.relative_to(ROOT).as_posix()}:{line} imports '{full}'. "
                    f"The '{layer}' layer cannot import from '{top}'. Move the shared logic down into "
                    f"'{layer}' (or 'core'), or call it from the '{top}' layer instead. "
                    "See ARCHITECTURE.md#layers."
                )
    assert not violations, "\n".join(violations)


def test_allocation_domain_is_pure():
    """core/allocation is the model itself: standard library and its own modules only."""
    violations = []
    for path in _python_files(PURE_PACKAGE):
        for line, top, full, level in _imports(path):
            if level > 0:
                continue                                  # relative import inside the package
            if top in STDLIB or full.startswith("core.allocation"):
                continue
            violations.append(
                f"{path.relative_to(ROOT).as_posix()}:{line} imports '{full}'. "
                "core/allocation must stay pure (no database, network, LLM or third-party package) so the "
                "model can be reproduced anywhere. Put I/O in modules/decision_allocation/ and pass plain "
                "data into the engine. See ARCHITECTURE.md#layers."
            )
    assert not violations, "\n".join(violations)


def test_model_numbers_live_only_in_the_config_file():
    """Weights and thresholds are stated once, in core/allocation/config/. Restating them in code
    or in the frontend lets copies drift."""
    threshold_literals = ("0.495", "0.667", "0.370", "0.620", "0.240", "0.295", "0.595")
    offenders = []
    for folder in ("core", "modules", "api", "loaders"):
        for path in _python_files(ROOT / folder):
            text = path.read_text(encoding="utf-8")
            hits = [t for t in threshold_literals if t in text]
            if len(hits) >= 3:
                offenders.append(f"{path.relative_to(ROOT).as_posix()} restates thresholds {hits}")
    frontend = ROOT / "frontend" / "src"
    if frontend.is_dir():
        for path in list(frontend.rglob("*.ts")) + list(frontend.rglob("*.tsx")):
            text = path.read_text(encoding="utf-8")
            hits = [t for t in threshold_literals if t in text]
            if len(hits) >= 3:
                offenders.append(f"{path.relative_to(ROOT).as_posix()} restates thresholds {hits}")
    assert not offenders, (
        "Model numbers must come from core/allocation/config/parth_v1_14.json via the API "
        "(GET /api/allocation/model), not be copied: " + "; ".join(offenders)
    )
