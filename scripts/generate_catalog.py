from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace import registrations, validate_release

CATALOG_TAG = "catalog-v1"
DOWNLOAD_ROOT = (
    "https://github.com/WinIslandProject/PluginMarketplace/releases/download/"
    f"{CATALOG_TAG}"
)


def revocations(path: Path) -> list[dict[str, str]]:
    with path.open("rb") as file:
        value = tomllib.load(file)
    if value.get("schema") != 1:
        raise ValueError("revocations.toml schema must be 1")
    entries = value.get("revocations", [])
    if not isinstance(entries, list):
        raise ValueError("revocations must be an array")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid revocation entry")
        plugin_id = entry.get("id")
        version = entry.get("version")
        reason = entry.get("reason")
        if not all(isinstance(item, str) and item for item in (plugin_id, version, reason)):
            raise ValueError("revocations require id, version, and reason")
        result.append({"id": plugin_id, "version": version, "reason": reason})
    return sorted(result, key=lambda entry: (entry["id"].casefold(), entry["version"]))


def icon_asset(plugin_id: str, source_name: str, data: bytes) -> str:
    suffix = Path(source_name).suffix.lower()
    digest = hashlib.sha256(data).hexdigest()
    return f"icons/{plugin_id}-{digest[:20]}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    signing_key = os.environ.get("MARKETPLACE_SIGNING_KEY")
    if not signing_key:
        raise ValueError("MARKETPLACE_SIGNING_KEY is required")
    key_bytes = base64.b64decode(signing_key, validate=True)
    if len(key_bytes) != 32:
        raise ValueError("MARKETPLACE_SIGNING_KEY must contain a raw Ed25519 private key")

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    plugins = []
    for registration in registrations(args.root):
        print(f"Publishing {registration.id}")
        release = validate_release(registration)
        icon_url = None
        if release.icon is not None and release.icon_name is not None:
            asset_name = icon_asset(registration.id, release.icon_name, release.icon)
            destination = args.output / asset_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(release.icon)
            icon_url = f"{DOWNLOAD_ROOT}/{asset_name}"
        plugins.append(
            {
                "id": registration.id,
                "name": release.name,
                "author": release.author,
                "version": release.version,
                "description": release.description,
                "repository": release.github_link,
                "source_commit": release.source_commit,
                "released_at": release.released_at,
                "download_url": release.download_url,
                "sha256": release.sha256,
                "size": release.size,
                "abi_version": release.abi_version,
                "min_winisland_version": registration.min_winisland_version,
                "categories": list(registration.categories),
                "readme": release.readme,
                "icon_url": icon_url,
            }
        )
    catalog = {
        "schema": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "plugins": sorted(plugins, key=lambda plugin: plugin["id"].casefold()),
        "revocations": revocations(args.root / "revocations.toml"),
    }
    catalog_bytes = json.dumps(
        catalog,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    signature = Ed25519PrivateKey.from_private_bytes(key_bytes).sign(catalog_bytes)
    (args.output / "catalog-v1.json").write_bytes(catalog_bytes)
    (args.output / "catalog-v1.sig").write_text(
        base64.b64encode(signature).decode("ascii"),
        encoding="ascii",
    )
    print(f"Published {len(plugins)} plugin(s)")


if __name__ == "__main__":
    main()
