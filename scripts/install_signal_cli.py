from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

OUT_BASE = Path(r"C:\Users\ADMIN\.openclaw\workspace")
TMP = OUT_BASE / "tmp"
DST = OUT_BASE / "bin" / "signal-cli"

API = "https://api.github.com/repos/AsamK/signal-cli/releases/latest"


def download(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out.write_bytes(r.read())


def pick_asset(rel: dict) -> dict:
    assets = rel.get("assets", [])

    # On Windows, avoid OS-native bundles (Linux-native/macos-native) and prefer the
    # generic distribution archives.
    cand = []
    for a in assets:
        name = (a.get("name") or "")
        lname = name.lower()
        url = a.get("browser_download_url")
        size = a.get("size") or 0
        if not url:
            continue
        if "signal-cli" not in lname:
            continue
        if "src" in lname:
            continue
        if any(x in lname for x in ("linux-native", "macos-native", "arm", "aarch64")):
            continue

        if lname.endswith(".zip"):
            score = 300
        elif lname.endswith(".tar.gz"):
            score = 200
        else:
            continue

        # Prefer the plain archive name (signal-cli-<ver>.zip) over anything else.
        if "-" in lname and "native" not in lname and "windows" not in lname:
            score += 50

        score += min(size / 1_000_000, 50)
        cand.append((score, a))

    if not cand:
        raise SystemExit("No suitable signal-cli asset (.tar.gz/.zip) found")

    cand.sort(key=lambda x: x[0], reverse=True)
    return cand[0][1]


def extract_tar_gz(archive: Path, dst: Path):
    # Use Windows tar (bsdtar) which exists on Win10+.
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["tar", "-xzf", str(archive), "-C", str(dst)])


def extract_zip(archive: Path, dst: Path):
    import zipfile

    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as z:
        z.extractall(dst)


def main():
    TMP.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(API, headers={"User-Agent": "openclaw"})
    with urllib.request.urlopen(req, timeout=60) as r:
        rel = json.load(r)

    chosen = pick_asset(rel)
    url = chosen["browser_download_url"]
    name = chosen["name"]

    archive_path = TMP / name

    print("release", rel.get("tag_name"))
    print("asset", name)
    print("downloading", url)
    download(url, archive_path)
    print("saved", archive_path, "bytes", archive_path.stat().st_size)

    # wipe old
    shutil.rmtree(DST, ignore_errors=True)
    DST.mkdir(parents=True, exist_ok=True)

    if name.lower().endswith(".tar.gz"):
        extract_tar_gz(archive_path, DST)
    elif name.lower().endswith(".zip"):
        extract_zip(archive_path, DST)
    else:
        raise SystemExit(f"Unsupported archive: {name}")

    # Find jar/bat(s)
    jars = list(DST.rglob("signal-cli*.jar"))
    bats = list(DST.rglob("signal-cli*.bat"))

    print("jars", len(jars))
    for j in jars[:5]:
        print("-", j)
    print("bats", len(bats))
    for b in bats[:5]:
        print("-", b)

    if not jars and not bats:
        raise SystemExit("Extraction succeeded but no signal-cli jar/bat found. Zip/tar layout may have changed.")


if __name__ == "__main__":
    main()
