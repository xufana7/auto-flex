#!/usr/bin/env python3
"""Read and update the persistent Auto Flex hardware profile."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

KEYS = (
    "DEFAULT_IP",
    "HEARD_Flex",
    "FLEX_ROBOT_NAME",
    "FLEX_API_VERSION",
    "FLEX_FIRMWARE_VERSION",
    "FLEX_SYSTEM_VERSION",
    "FLEX_ROBOT_MODEL",
    "FLEX_ROBOT_SERIAL",
    "FLEX_HARDWARE_UPDATED_AT",
)

DEFAULTS = {
    "DEFAULT_IP": "169.254.224.1",
    "HEARD_Flex": "False",
    "FLEX_ROBOT_NAME": "",
    "FLEX_API_VERSION": "",
    "FLEX_FIRMWARE_VERSION": "",
    "FLEX_SYSTEM_VERSION": "",
    "FLEX_ROBOT_MODEL": "",
    "FLEX_ROBOT_SERIAL": "",
    "FLEX_HARDWARE_UPDATED_AT": "",
}


def read_env(path: Path) -> dict[str, str]:
    values = dict(DEFAULTS)
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in values:
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def clean(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Auto Flex persistent hardware profile"]
    lines.extend(f"{key}={clean(values.get(key, ''))}" for key in KEYS)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def status_payload(path: Path, values: dict[str, str]) -> dict[str, object]:
    heard = values["HEARD_Flex"].casefold() == "true"
    return {
        "env": str(path),
        "needs_hardware_sync": not heard,
        "hardware": values,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, help="Path to the Auto Flex .env file")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    write_parser = subparsers.add_parser("write-health")
    write_parser.add_argument("--robot-name", required=True)
    write_parser.add_argument("--api-version", required=True)
    write_parser.add_argument("--firmware-version", required=True)
    write_parser.add_argument("--system-version", required=True)
    write_parser.add_argument("--robot-model", required=True)
    write_parser.add_argument("--robot-serial", required=True)
    subparsers.add_parser("reset")
    args = parser.parse_args()

    env_path = Path(args.env).resolve()
    values = read_env(env_path)
    if args.command == "write-health":
        values.update({
            "HEARD_Flex": "True",
            "FLEX_ROBOT_NAME": clean(args.robot_name),
            "FLEX_API_VERSION": clean(args.api_version),
            "FLEX_FIRMWARE_VERSION": clean(args.firmware_version),
            "FLEX_SYSTEM_VERSION": clean(args.system_version),
            "FLEX_ROBOT_MODEL": clean(args.robot_model),
            "FLEX_ROBOT_SERIAL": clean(args.robot_serial),
            "FLEX_HARDWARE_UPDATED_AT": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        write_env(env_path, values)
    elif args.command == "reset":
        default_ip = values.get("DEFAULT_IP") or DEFAULTS["DEFAULT_IP"]
        values = dict(DEFAULTS)
        values["DEFAULT_IP"] = default_ip
        write_env(env_path, values)

    print(json.dumps(status_payload(env_path, values), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

