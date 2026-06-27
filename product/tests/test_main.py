# tests/test_project_structure.py
import importlib
import inspect
import pathlib
import re

import pytest

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def import_module(module_path: str):
    """
    Import a module by its dotted path and return the module object.
    Raise an informative AssertionError if the import fails.
    """
    try:
        return importlib.import_module(module_path)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Unable to import module '{module_path}': {exc}")


def read_file(relative_path: str) -> str:
    """
    Return the text contents of a file relative to the repository root.
    """
    root = pathlib.Path(__file__).resolve().parents[1]  # project root (tests/..)
    file_path = root / relative_path
    if not file_path.is_file():
        pytest.fail(f"Expected file '{relative_path}' does not exist.")
    return file_path.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# Tests for app/__init__.py
# ----------------------------------------------------------------------
def test_app_init_importable():
    """`app/__init__.py` must be importable without side‑effects."""
    import_module("app")


# ----------------------------------------------------------------------
# Tests for app/main.py
# ----------------------------------------------------------------------
def test_main_importable():
    """`app/main.py` must be importable."""
    import_module("app.main")


def test_main_contains_fastapi_app():
    """
    The `app.main` module should expose a FastAPI instance named ``app``.
    The test only checks the type name to avoid requiring FastAPI at import time.
    """
    mod = import_module("app.main")
    assert hasattr(mod, "app"), "app.main should expose a variable called 'app'"
    app_obj = getattr(mod, "app")
    # The object should look like a FastAPI instance (has `router` and `title` attributes)
    assert hasattr(app_obj, "router"), "FastAPI app should have a `router` attribute"
    assert hasattr(app_obj, "title"), "FastAPI app should have a `title` attribute"


# ----------------------------------------------------------------------
# Tests for app/schemas.py
# ----------------------------------------------------------------------
def test_schemas_importable():
    """`app/schemas.py` must be importable."""
    import_module("app.schemas")


def test_schemas_define_pydantic_models():
    """
    Verify that the module defines at least one subclass of `pydantic.BaseModel`.
    The test does not depend on a concrete model name.
    """
    mod = import_module("app.schemas")
    # Import BaseModel lazily – if pydantic is missing we skip the test rather than error.
    try:
        from pydantic import BaseModel
    except Exception:  # pragma: no cover
        pytest.skip("pydantic is not installed; cannot validate schema classes.")

    # Find subclasses of BaseModel defined in the module
    model_classes = [
        obj
        for name, obj in inspect.getmembers(mod, inspect.isclass)
        if issubclass(obj, BaseModel) and obj is not BaseModel
    ]
    assert model_classes, "No Pydantic BaseModel subclasses found in app.schemas"


# ----------------------------------------------------------------------
# Tests for app/database.py
# ----------------------------------------------------------------------
def test_database_importable():
    """`app/database.py` must be importable."""
    import_module("app.database")


def test_database_exposes_engine_and_session():
    """
    The database module should expose a SQLAlchemy ``engine`` and a ``SessionLocal`` callable.
    The test only checks attribute existence and simple type hints.
    """
    mod = import_module("app.database")
    # Basic attribute checks
    assert hasattr(mod, "engine"), "app.database must define an `engine` attribute"
    assert hasattr(mod, "SessionLocal"), "app.database must define a `SessionLocal` attribute"

    engine = getattr(mod, "engine")
    SessionLocal = getattr(mod, "SessionLocal")

    # Avoid importing SQLAlchemy in environments where it may not be installed.
    try:
        from sqlalchemy.engine import Engine
        from sqlalchemy.orm import Session
    except Exception:  # pragma: no cover
        pytest.skip("SQLAlchemy not installed; skipping detailed engine checks.")

    assert isinstance(engine, Engine), "`engine` should be an instance of sqlalchemy.engine.Engine"
    # SessionLocal is usually a sessionmaker, callable returning a Session
    assert callable(SessionLocal), "`SessionLocal` should be callable (sessionmaker)"
    # A quick sanity check: calling it should return a Session (or raise if DB URL missing)
    try:
        sess = SessionLocal()
        assert isinstance(sess, Session), "`SessionLocal()` should return a sqlalchemy.orm.Session"
        sess.close()
    except Exception:
        # If DB connection string is missing the call may raise; that's acceptable for this test.
        pass


# ----------------------------------------------------------------------
# Tests for Dockerfile
# ----------------------------------------------------------------------
def test_dockerfile_exists():
    """Dockerfile should exist at the repository root."""
    content = read_file("Dockerfile")
    assert content, "Dockerfile is empty"


def test_dockerfile_has_basic_structure():
    """
    Very lightweight sanity checks for a typical FastAPI Dockerfile.
    Looks for a FROM line, a working directory definition and a CMD/ENTRYPOINT.
    """
    content = read_file("Dockerfile")
    lines = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    # Must contain a FROM statement
    assert any(ln.startswith("FROM") for ln in lines), "Dockerfile should contain a FROM statement"

    # Must set a working directory (commonly /app)
    assert any(ln.startswith("WORKDIR") for ln in lines), "Dockerfile should contain a WORKDIR statement"

    # Must expose a port (commonly 80 or 8000)
    assert any(ln.startswith("EXPOSE") for ln in lines), "Dockerfile should contain an EXPOSE statement"

    # Must have a CMD or ENTRYPOINT that starts uvicorn or similar
    has_cmd = any(ln.startswith("CMD") for ln in lines)
    has_entry = any(ln.startswith("ENTRYPOINT") for ln in lines)
    assert has_cmd or has_entry, "Dockerfile should contain CMD or ENTRYPOINT"


# ----------------------------------------------------------------------
# Tests for requirements.txt
# ----------------------------------------------------------------------
def test_requirements_exists():
    """requirements.txt should exist and be non‑empty."""
    content = read_file("requirements.txt")
    assert content.strip(), "requirements.txt is empty"


def test_requirements_contains_essential_packages():
    """
    Check that common FastAPI project dependencies are listed.
    The test is tolerant – it only warns if none of the expected packages appear.
    """
    content = read_file("requirements.txt")
    lines = [ln.strip().lower() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]

    expected = {"fastapi", "uvicorn", "pydantic", "sqlalchemy"}
    found = {pkg for pkg in expected if any(pkg in line for line in lines)}
    assert found, f"None of the expected packages {expected} were found in requirements.txt"
    # It's ok if only a subset appears; we just ensure at least one expected dep is present.


# ----------------------------------------------------------------------
# Tests for README.md
# ----------------------------------------------------------------------
def test_readme_exists():
    """README.md should exist and be non‑empty."""
    content = read_file("README.md")
    assert content.strip(), "README.md is empty"


def test_readme_contains_title_and_description():
    """
    Basic checks: first non‑comment line should be a Markdown H1,
    and somewhere later there should be a short description (a plain paragraph).
    """
    content = read_file("README.md")
    lines = [ln.rstrip() for ln in content.splitlines() if ln.strip()]

    # Find first header line
    header = next((ln for ln in lines if ln.startswith("#")), None)
    assert header, "README.md should contain at least one Markdown heading"
    assert re.match(r"^#+\s+.+", header), "The first heading should be a valid H1/H2 style"

    # Look for a non‑heading paragraph after the first heading
    after_header = lines[lines.index(header) + 1 :]
    paragraph = next((ln for ln in after_header if not ln.startswith("#")), None)
    assert paragraph and len(paragraph) > 20, "README.md should contain a descriptive paragraph after the title"


# ----------------------------------------------------------------------
# End of test suite
# ----------------------------------------------------------------------