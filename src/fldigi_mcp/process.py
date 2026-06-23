"""Launch, monitor, and stop the fldigi application process.

Cross-platform: macOS, Windows, and Linux (including Raspberry Pi). This is
optional — the server works fine against an already-running fldigi. It just lets
the server start one (and stop one it started) when asked, supporting
human-in-the-loop and headless/unattended setups.

Headless mode is POSIX-only (Linux/macOS); fldigi's `--xmlrpc-server-*` switches
are passed so the launched instance is reachable at the configured endpoint.
"""

from __future__ import annotations

import glob
import shutil
import subprocess
import sys
import time
import xmlrpc.client

# Standard install locations to search if fldigi is not on PATH.
_MAC_GLOBS = [
    "/Applications/fldigi*.app/Contents/MacOS/fldigi",
    "/Applications/Fldigi*.app/Contents/MacOS/fldigi",
]
_WIN_GLOBS = [
    r"C:\Program Files\Fldigi*\fldigi.exe",
    r"C:\Program Files (x86)\Fldigi*\fldigi.exe",
]
_LINUX_GLOBS = [
    "/usr/bin/fldigi",
    "/usr/local/bin/fldigi",
]


def find_executable(explicit: str | None = None) -> str | None:
    """Locate the fldigi executable: explicit path, then PATH, then known dirs."""
    if explicit:
        return explicit if shutil.which(explicit) or _exists(explicit) else None
    found = shutil.which("fldigi")
    if found:
        return found
    if sys.platform == "darwin":
        globs = _MAC_GLOBS
    elif sys.platform.startswith("win"):
        globs = _WIN_GLOBS
    else:
        globs = _LINUX_GLOBS
    for pattern in globs:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]  # newest-sorted
    return None


def _exists(path: str) -> bool:
    import os

    return os.path.isfile(path)


class FldigiProcess:
    """Owns the lifecycle of a fldigi process the server launched."""

    def __init__(self, host: str, port: int, executable: str | None = None) -> None:
        self.host = host
        self.port = port
        self.executable = executable
        self._proc: subprocess.Popen | None = None
        self._url = f"http://{host}:{port}/"

    def _api_alive(self) -> bool:
        try:
            xmlrpc.client.ServerProxy(self._url, allow_none=True).fldigi.name_version()
            return True
        except Exception:
            return False

    def is_running(self) -> bool:
        """True if a launched process is still alive, or the API answers."""
        if self._proc is not None and self._proc.poll() is None:
            return True
        return self._api_alive()

    def launch(
        self,
        extra_args: list[str] | None = None,
        ready_timeout: float = 30.0,
    ) -> dict:
        """Start fldigi and wait until its XML-RPC server answers.

        Only the XML-RPC endpoint switches are passed by default, so the launched
        instance is reachable at the configured host/port. Pass ``extra_args`` for
        anything else (e.g. ``--config-dir``). Headless operation on Linux is done
        by wrapping the launch with ``xvfb-run`` at the OS level, not a fldigi flag.
        """
        if self._api_alive():
            return {"launched": False, "reason": "fldigi is already running / reachable."}
        exe = find_executable(self.executable)
        if exe is None:
            raise FileNotFoundError(
                "Could not find the fldigi executable. Set its path explicitly."
            )
        args = [
            exe,
            "--xmlrpc-server-address",
            self.host,
            "--xmlrpc-server-port",
            str(self.port),
        ]
        if extra_args:
            args.extend(extra_args)

        self._proc = subprocess.Popen(args)
        deadline = time.time() + ready_timeout
        while time.time() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError(f"fldigi exited during startup (code {self._proc.returncode}).")
            if self._api_alive():
                return {"launched": True, "executable": exe, "endpoint": self._url}
            time.sleep(0.5)
        raise TimeoutError("fldigi did not become reachable within the timeout.")

    def stop(self, save_bitmask: int = 0, force_after: float = 5.0) -> dict:
        """Ask fldigi to terminate gracefully; fall back to killing if needed.

        `save_bitmask` follows fldigi.terminate: 0=options, 1=log, 2=macros.
        """
        graceful = False
        try:
            xmlrpc.client.ServerProxy(self._url, allow_none=True).fldigi.terminate(save_bitmask)
            graceful = True
        except Exception:
            pass

        if self._proc is None:
            return {
                "stopped": graceful,
                "method": "xmlrpc" if graceful else "none",
                "note": "Server did not launch this fldigi; asked it to quit via API.",
            }

        deadline = time.time() + force_after
        while time.time() < deadline:
            if self._proc.poll() is not None:
                return {"stopped": True, "method": "graceful" if graceful else "exit"}
            time.sleep(0.25)
        self._proc.terminate()
        try:
            self._proc.wait(timeout=force_after)
            return {"stopped": True, "method": "terminate"}
        except subprocess.TimeoutExpired:
            self._proc.kill()
            return {"stopped": True, "method": "kill"}
