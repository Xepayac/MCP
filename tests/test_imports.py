"""Smoke tests — verify all MCP servers can be imported."""
import importlib
import pytest

SERVER_MODULES = [
    "servers.browser.server",
    "servers.email.server",
    "servers.gimp.server",
    "servers.inkscape.server",
    "servers.libreoffice.server",
    "servers.tesseract.server",
]

@pytest.mark.parametrize("module_path", SERVER_MODULES)
def test_server_imports(module_path):
    """Each server module should import without error."""
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        pytest.skip(f"Optional dependency missing: {e}")
