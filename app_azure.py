"""Azure App Service / Oryx entrypoint — exposes `app` for gunicorn/uvicorn."""
import glob
import os
import shutil
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (_ROOT, "/home/site/wwwroot", *sorted(glob.glob("/tmp/8dee*"))):
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Persist ChromaDB onto the Azure home share when Oryx extract is ephemeral.
_dst = os.environ.get("CHROMA_PERSIST_DIR", "/home/site/wwwroot/chroma_db")
os.makedirs(_dst, exist_ok=True)
for _d in sorted(glob.glob("/tmp/8dee*")):
    _src = os.path.join(_d, "chroma_db")
    if not os.path.isdir(_src):
        continue
    for _name in os.listdir(_src):
        _s = os.path.join(_src, _name)
        _t = os.path.join(_dst, _name)
        try:
            if os.path.isdir(_s):
                if os.path.exists(_t):
                    shutil.rmtree(_t)
                shutil.copytree(_s, _t)
            else:
                shutil.copy2(_s, _t)
        except OSError:
            pass
    break

from api.main import app  # noqa: E402,F401
