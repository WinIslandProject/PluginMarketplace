from __future__ import annotations

import argparse
from pathlib import Path

from marketplace import registrations, validate_release


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--skip-attestations", action="store_true")
    args = parser.parse_args()
    entries = registrations(args.root)
    for entry in entries:
        print(f"Validating {entry.id} from {entry.repository}")
        release = validate_release(entry, verify_attestation=not args.skip_attestations)
        print(f"Accepted {entry.id} {release.version} ({release.sha256})")
    print(f"Validated {len(entries)} plugin registration(s)")


if __name__ == "__main__":
    main()
