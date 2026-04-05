"""Environment cleanup for subprocess calls.

VS Code runs as a snap, injecting snap's glibc into library paths.
Apt-installed CLI tools (Inkscape, LibreOffice, Tesseract) pick up
the wrong libraries and crash. This module strips snap contamination.
"""

import os


def clean_env() -> dict[str, str]:
    """Return environment with snap contamination removed."""
    env = {}
    for k, v in os.environ.items():
        if k.startswith("SNAP"):
            continue
        if "snap" in v and k in (
            "GTK_PATH", "GTK_EXE_PREFIX", "GTK_IM_MODULE_FILE",
            "GDK_PIXBUF_MODULE_FILE", "GDK_PIXBUF_MODULEDIR",
            "GIO_MODULE_DIR", "GSETTINGS_SCHEMA_DIR", "LOCPATH",
            "LD_LIBRARY_PATH", "LD_PRELOAD",
        ):
            continue
        if k in ("PATH", "XDG_DATA_DIRS", "XDG_DATA_HOME"):
            v = ":".join(p for p in v.split(":") if "snap" not in p)
            if not v:
                continue
        env[k] = v
    return env
