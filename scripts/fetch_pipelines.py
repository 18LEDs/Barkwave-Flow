#!/usr/bin/env python3
"""Fetch Datadog log pipeline configurations and store them as JSON files.

The script queries the Datadog API for the specified pipeline names and writes
the resulting configuration JSON into the `pipelines/` directory. These files
can then be managed as configuration-as-code and consumed by Terraform.

Usage:
    DATADOG_API_KEY=xxx DATADOG_APP_KEY=yyy scripts/fetch_pipelines.py [names...]

If no pipeline names are supplied, a default list of six Kubernetes related
pipelines (nonprod and prod) is fetched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Dict

import requests

DEFAULT_PIPELINES = [
    "k8-aws-nonprod",
    "k8-azure-nonprod",
    "k8-onprem-nonprod",
    "k8-aws-prod",
    "k8-azure-prod",
    "k8-onprem-prod",
]

API_BASE = os.environ.get("DATADOG_API_URL", "https://api.datadoghq.com")


def api_headers() -> Dict[str, str]:
    try:
        api_key = os.environ["DATADOG_API_KEY"]
        app_key = os.environ["DATADOG_APP_KEY"]
    except KeyError as e:
        print(f"Missing required environment variable: {e.args[0]}", file=sys.stderr)
        sys.exit(1)
    return {
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
        "Content-Type": "application/json",
    }


def list_pipelines() -> Iterable[Dict[str, str]]:
    url = f"{API_BASE}/api/v1/logs/config/pipelines"
    resp = requests.get(url, headers=api_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_pipeline(pipeline_id: str) -> Dict:
    url = f"{API_BASE}/api/v1/logs/config/pipelines/{pipeline_id}"
    resp = requests.get(url, headers=api_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_pipeline(name: str, data: Dict) -> None:
    pipelines_dir = Path(__file__).resolve().parent.parent / "pipelines"
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    path = pipelines_dir / f"{name}.json"
    with path.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Saved {name} -> {path}")


def fetch_and_save(names: Iterable[str]) -> None:
    existing = {p["name"]: p["id"] for p in list_pipelines()}
    for name in names:
        pipeline_id = existing.get(name)
        if not pipeline_id:
            print(f"Warning: pipeline '{name}' not found in Datadog", file=sys.stderr)
            continue
        data = get_pipeline(pipeline_id)
        save_pipeline(name, data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Datadog log pipeline configs")
    parser.add_argument(
        "pipelines",
        nargs="*",
        default=DEFAULT_PIPELINES,
        help="Names of pipelines to fetch (default: six k8 pipelines)",
    )
    args = parser.parse_args()
    fetch_and_save(args.pipelines)


if __name__ == "__main__":
    main()
