"""Architectural conformance tests.

The layering rules in the engineering standards are enforced here rather than
left as convention. Every check parses the source with :mod:`ast` instead of
importing it, so a violation is reported as a readable assertion naming the
file and the offending construct.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "papermint"
PROJECT_ROOT = PACKAGE_ROOT.parent

#: Packages that must never import Streamlit.
DOMAIN_PACKAGES = ("extractors", "parsers", "enrichment", "exporters", "formatters")

#: Domain modules that live directly in the package root.
DOMAIN_MODULES = ("models.py", "config.py", "errors.py", "pipeline.py")


def _domain_files() -> list[Path]:
    """Collect every source file belonging to the domain layer.

    Returns:
        The domain layer's Python files.
    """
    files = [PACKAGE_ROOT / name for name in DOMAIN_MODULES]
    for package in DOMAIN_PACKAGES:
        files.extend(sorted((PACKAGE_ROOT / package).rglob("*.py")))
    return [f for f in files if f.exists()]


def _all_package_files() -> list[Path]:
    """Collect every source file in the package.

    Returns:
        Every Python file under ``papermint/``.
    """
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _imported_roots(path: Path) -> set[str]:
    """Return the top-level module names imported by a file.

    Args:
        path: The source file to inspect.

    Returns:
        The root package name of every import statement.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _dotted_imports(path: Path) -> set[str]:
    """Return the full dotted module paths imported by a file.

    Args:
        path: The source file to inspect.

    Returns:
        Every imported module path.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _relative(path: Path) -> str:
    """Return a path relative to the project root, for assertion messages.

    Args:
        path: An absolute path inside the project.

    Returns:
        The relative path as a string.
    """
    return str(path.relative_to(PROJECT_ROOT))


# --- Layering --------------------------------------------------------------


@pytest.mark.parametrize("path", _domain_files(), ids=_relative)
def test_the_domain_layer_never_imports_streamlit(path: Path):
    assert "streamlit" not in _imported_roots(path), (
        f"{_relative(path)} imports Streamlit. The domain layer must run headless."
    )


@pytest.mark.parametrize("path", _domain_files(), ids=_relative)
def test_the_domain_layer_never_imports_the_ui(path: Path):
    offenders = {m for m in _dotted_imports(path) if m.startswith("papermint.ui")}
    assert not offenders, f"{_relative(path)} imports the presentation layer: {sorted(offenders)}"


def test_the_pipeline_is_importable_headless():
    from papermint.pipeline import PipelineService

    assert PipelineService is not None
    assert "streamlit" not in _imported_roots(PACKAGE_ROOT / "pipeline.py")


# --- Coding standards ------------------------------------------------------


@pytest.mark.parametrize("path", _all_package_files(), ids=_relative)
def test_no_module_uses_print(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert not calls, (
        f"{_relative(path)} calls print() at line {calls[0].lineno}. Use a module logger instead."
    )


@pytest.mark.parametrize("path", _all_package_files(), ids=_relative)
def test_no_module_uses_a_bare_except(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    bare = [
        node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler) and node.type is None
    ]
    assert not bare, (
        f"{_relative(path)} has a bare except at line {bare[0].lineno}. "
        "Catch a specific exception type."
    )


@pytest.mark.parametrize(
    "path", [p for p in _all_package_files() if p.name != "__init__.py"], ids=_relative
)
def test_every_module_uses_postponed_annotations(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )
    assert has_future, f"{_relative(path)} is missing 'from __future__ import annotations'."


@pytest.mark.parametrize(
    "path", [p for p in _all_package_files() if p.name != "__init__.py"], ids=_relative
)
def test_every_module_and_public_definition_is_documented(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert ast.get_docstring(tree), f"{_relative(path)} has no module docstring."

    undocumented = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
        and not ast.get_docstring(node)
    ]
    assert not undocumented, (
        f"{_relative(path)} has undocumented public definitions: {undocumented}"
    )


# --- Presentation ----------------------------------------------------------


def test_pages_do_not_reach_past_the_pipeline_service():
    for path in sorted((PACKAGE_ROOT / "ui" / "pages").glob("*.py")):
        offenders = {
            module
            for module in _dotted_imports(path)
            if module.startswith(("papermint.parsers", "papermint.extractors."))
        }
        assert not offenders, (
            f"{_relative(path)} reaches past the pipeline service into {sorted(offenders)}"
        )


def test_the_entry_point_delegates_routing():
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "build_navigation" in source
    assert "st.Page(" not in source
