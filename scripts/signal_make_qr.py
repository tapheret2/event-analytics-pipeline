from __future__ import annotations

import os
import re
import sys
import subprocess
from pathlib import Path


def find_signal_cli_jar(base: Path) -> Path | None:
    if not base.exists():
        return None
    jars = [p for p in base.rglob("signal-cli*.jar") if p.is_file()]
    # exclude sources/javadoc
    jars = [p for p in jars if not re.search(r"sources|javadoc", p.name, re.I)]
    if not jars:
        return None
    jars.sort(key=lambda p: p.stat().st_size, reverse=True)
    return jars[0]


def ensure_qrcode():
    try:
        import qrcode  # noqa
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"])


def main():
    workspace = Path(r"C:\Users\ADMIN\.openclaw\workspace")
    base = workspace / "bin" / "signal-cli"
    cfg = Path(r"C:\Users\ADMIN\.openclaw\signal-cli")
    cfg.mkdir(parents=True, exist_ok=True)

    jar = find_signal_cli_jar(base)
    if jar is None:
        installer = workspace / "scripts" / "install_signal_cli.py"
        if installer.exists():
            subprocess.check_call([sys.executable, str(installer)])
            jar = find_signal_cli_jar(base)

    if jar is None:
        raise SystemExit(f"Could not find signal-cli jar under {base}")

    # Find a compatible Java runtime.
    # signal-cli v0.14+ may require very new Java, so we prefer a bundled Temurin JDK if present.
    java_exe = None
    bundled = workspace / "bin" / "temurin-jdk25"
    if bundled.exists():
        for pth in bundled.rglob("java.exe"):
            java_exe = str(pth)
            break

    if java_exe is None:
        java_exe = "java"

    # Run link and capture stdout. signal-cli prints a QR and/or a link URI.
    cmd = [java_exe, "-jar", str(jar), "-c", str(cfg), "link", "-n", "OpenClaw"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + "\n" + (p.stderr or "")

    # Extract a URI if present
    m = re.search(r"(sgnl://[^\s]+|tsdevice:[^\s]+|https?://[^\s]+)", out)
    if not m:
        # Write log for debugging
        log = Path.home() / "Desktop" / "signal_qr_log.txt"
        log.write_text(out, encoding="utf-8")
        raise SystemExit(f"signal-cli did not print a link URI. See log: {log}")

    uri = m.group(1)

    ensure_qrcode()
    import qrcode

    img = qrcode.make(uri)
    out_png = Path.home() / "Desktop" / "signal_link_qr.png"
    img.save(out_png)

    # Also save the URI for reference
    (Path.home() / "Desktop" / "signal_link_uri.txt").write_text(uri + "\n", encoding="utf-8")

    print(f"OK: wrote {out_png}")
    print("URI:", uri)


if __name__ == "__main__":
    main()
