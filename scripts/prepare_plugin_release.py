from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

PLUGIN_ID = re.compile(r"^[A-Za-z0-9_-]{1,63}$")
VERSION = re.compile(r"^[A-Za-z0-9.+-]{1,31}$")


def manifest_value(text: str, key: str) -> str:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip("'\"")
    raise ValueError(f"plugin.yml is missing {key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packages = sorted(args.root.glob("target/*.zip"))
    if len(packages) != 1:
        raise ValueError(f"expected one target/*.zip package, found {len(packages)}")
    source = packages[0]
    with zipfile.ZipFile(source) as archive:
        manifest = archive.read("plugin.yml").decode("utf-8")
    plugin_id = manifest_value(manifest, "id")
    version = manifest_value(manifest, "version")
    if not PLUGIN_ID.fullmatch(plugin_id) or not VERSION.fullmatch(version):
        raise ValueError("plugin.yml contains an invalid ID or version")
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f"{plugin_id}-{version}.winisland-plugin.zip"
    shutil.copyfile(source, destination)
    print(destination.resolve())


if __name__ == "__main__":
    main()
