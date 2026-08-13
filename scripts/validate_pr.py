from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def main() -> None:
    event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        raise ValueError("pull request event is required")
    files_url = pull.get("url", "") + "/files?per_page=100"
    request = urllib.request.Request(
        files_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "User-Agent": "WinIsland-PluginMarketplace",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        files = json.load(response)
    registrations = []
    for changed in files:
        name = changed.get("filename", "")
        status = changed.get("status")
        if not name.startswith("plugins/") or not name.endswith(".toml"):
            raise ValueError(f"contributor PRs may only add plugin registrations: {name}")
        if status != "added":
            raise ValueError(f"contributor PRs may not modify existing registrations: {name}")
        registrations.append(name)
    if len(registrations) != 1:
        raise ValueError("a contributor PR must add exactly one plugin registration")
    print(f"Accepted pull request shape: {registrations[0]}")


if __name__ == "__main__":
    main()
