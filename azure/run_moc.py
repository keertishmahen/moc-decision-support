"""Azure App Service launcher — runs from Oryx extract or wwwroot."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys


def log(msg: str) -> None:
    sys.stderr.write(f"[moc] {msg}\n")
    sys.stderr.flush()


def find_root() -> str:
    cands = sorted(glob.glob("/tmp/8dee*")) + ["/home/site/wwwroot"]
    for d in cands:
        if os.path.isdir(os.path.join(d, "api")) and os.path.isfile(
            os.path.join(d, "antenv", "bin", "python")
        ):
            return d
    for d in cands:
        if os.path.isfile(os.path.join(d, "antenv", "bin", "python")):
            return d
    raise SystemExit("FATAL: no antenv under /tmp/8dee* or wwwroot")


def ensure_pkgs(root: str, py: str, sp: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = root + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
    probe = subprocess.run(
        [py, "-c", "import api; print(api.__file__)"],
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
    )
    if probe.returncode == 0:
        log(f"api ok: {(probe.stdout or '').strip()}")
        return
    log(f"api missing, copying into site-packages ({(probe.stderr or '')[:200]})")
    if not os.path.isdir(sp):
        raise SystemExit(f"FATAL: site-packages missing: {sp}")
    for pkg in ("api", "core", "modules"):
        src = os.path.join(root, pkg)
        dst = os.path.join(sp, pkg)
        if not os.path.isdir(src):
            continue
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        log(f"copied {pkg}")
    app_src = os.path.join(root, "app.py")
    if os.path.isfile(app_src):
        shutil.copy2(app_src, os.path.join(sp, "app.py"))


def main() -> None:
    root = find_root()
    log(f"root={root}")
    py = os.path.join(root, "antenv", "bin", "python")
    sp = os.path.join(root, "antenv", "lib", "python3.11", "site-packages")
    os.environ["CHROMA_PERSIST_DIR"] = os.environ.get(
        "CHROMA_PERSIST_DIR", "/home/site/wwwroot/chroma_db"
    )
    os.makedirs(os.environ["CHROMA_PERSIST_DIR"], exist_ok=True)
    os.environ["PYTHONPATH"] = root + (
        (":" + os.environ["PYTHONPATH"]) if os.environ.get("PYTHONPATH") else ""
    )
    ensure_pkgs(root, py, sp)
    os.chdir(root)
    os.execv(
        py,
        [
            py,
            "-m",
            "gunicorn",
            "--bind=0.0.0.0:8000",
            "--timeout",
            "120",
            "-w",
            "1",
            "-k",
            "uvicorn.workers.UvicornWorker",
            "--chdir",
            root,
            "--pythonpath",
            root,
            "api.main:app",
        ],
    )


if __name__ == "__main__":
    main()
