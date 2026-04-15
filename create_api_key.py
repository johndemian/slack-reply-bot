#!/usr/bin/env python3
"""
Create an Anthropic API key using the Admin API.

Requires an admin API key set as ANTHROPIC_ADMIN_KEY in your environment
or .env file. Admin keys can be created at:
https://console.anthropic.com/settings/admin-keys

Usage:
    python create_api_key.py
    python create_api_key.py --name my-bot-key
    python create_api_key.py --name my-bot-key --update-env
    python create_api_key.py --name my-bot-key --workspace-id wrkspc-xxxx
"""

import argparse
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
ADMIN_API_BETA = "api-management-2025-02-19"


def create_api_key(admin_key: str, name: str, workspace_id: str = None) -> dict:
    """Create a new Anthropic API key via the Admin API."""
    headers = {
        "x-api-key": admin_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": ADMIN_API_BETA,
        "content-type": "application/json",
    }
    body = {"name": name}
    if workspace_id:
        body["workspace_id"] = workspace_id

    response = requests.post(
        f"{ANTHROPIC_API_BASE}/v1/api_keys",
        headers=headers,
        json=body,
    )

    if not response.ok:
        print(f"Error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)

    return response.json()


def update_env_file(env_path: str, api_key: str) -> None:
    """Update ANTHROPIC_API_KEY in the .env file."""
    with open(env_path, "r") as f:
        content = f.read()

    updated = re.sub(
        r"^ANTHROPIC_API_KEY=.*$",
        f"ANTHROPIC_API_KEY={api_key}",
        content,
        flags=re.MULTILINE,
    )

    with open(env_path, "w") as f:
        f.write(updated)


def main():
    parser = argparse.ArgumentParser(
        description="Create an Anthropic API key via the Admin API."
    )
    parser.add_argument(
        "--name",
        default="slack-reply-bot",
        help="Display name for the new API key (default: slack-reply-bot)",
    )
    parser.add_argument(
        "--workspace-id",
        dest="workspace_id",
        help="Workspace ID to scope the key to (optional)",
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Automatically write the new key to .env as ANTHROPIC_API_KEY",
    )
    args = parser.parse_args()

    admin_key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if not admin_key:
        print(
            "Error: ANTHROPIC_ADMIN_KEY is not set.\n"
            "Create an admin key at https://console.anthropic.com/settings/admin-keys\n"
            "then add it to your .env file:\n\n"
            "  ANTHROPIC_ADMIN_KEY=sk-ant-admin-xxxx",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Creating API key '{args.name}'...")
    result = create_api_key(admin_key, args.name, args.workspace_id)

    key_id = result.get("id", "")
    # The secret value is only returned on creation
    secret_key = result.get("secret_key") or result.get("key") or result.get("api_key", "")

    print(f"\nAPI key created successfully!")
    print(f"  Name: {result.get('name', args.name)}")
    print(f"  ID:   {key_id}")
    print(f"  Key:  {secret_key}")
    print("\nIMPORTANT: Save this key now — it will not be shown again.")

    if args.update_env:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            update_env_file(env_path, secret_key)
            print(f"\nUpdated ANTHROPIC_API_KEY in {env_path}")
        else:
            print(
                f"\nWarning: .env file not found at {env_path}. "
                "Run `cp .env.example .env` first.",
                file=sys.stderr,
            )
    else:
        print("\nTo use this key, add it to your .env file:")
        print(f"  ANTHROPIC_API_KEY={secret_key}")


if __name__ == "__main__":
    main()
