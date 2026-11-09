#!/usr/bin/env python3
"""Guide the user through obtaining and optionally saving an ADS API key."""

import getpass
import os
import shlex
import tempfile
import webbrowser
from pathlib import Path

import ads_scix


def confirm(message: str) -> bool:
    return input(f"{message} [y/N] ").strip().lower() in ("y", "yes")


def main() -> None:
    try:
        ads_scix.token()
    except SystemExit:
        pass
    else:
        print("ADS/SciX credentials are already available; setup skipped. They have not been validated online.")
        return

    url = "https://ui.adsabs.harvard.edu/user/settings/token"
    print("Step 1/2: Obtain an ADS API key")
    print(f"Open {url}, sign in, and find your API token in your user profile.")
    print("If needed, choose 'Generate a new key'; check whether this affects an existing key.")
    if confirm("Open the ADS token page in your browser?"):
        webbrowser.open(url)
    input("Copy the key, then press Enter. ")

    config_dir = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    credentials = config_dir / "absads" / "credentials"
    print(f"Step 2/2: Optionally save the key locally at {credentials}")
    if not confirm("Save the key for automatic use by the ADS helper?"):
        print("No key saved. Set ADS_API_KEY or SCIX_API_KEY in the agent's environment to use ADS.")
        return
    if credentials.is_symlink() or (credentials.exists() and not credentials.is_file()):
        raise SystemExit("Credentials path is not a regular file; no changes made.")
    if credentials.exists() and not confirm("Update the existing credentials file?"):
        print("No changes made.")
        return
    value = getpass.getpass("Paste the ADS API key (input hidden): ")
    if not value or any(c in value for c in "\r\n\0"):
        raise SystemExit("A nonempty single-line key is required; no changes made.")

    credentials.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    old = credentials.read_text(encoding="utf-8").splitlines() if credentials.exists() else []
    lines = [line for line in old if not line.startswith("ADS_API_KEY=")]
    lines.append("ADS_API_KEY=" + shlex.quote(value))
    fd, temporary = tempfile.mkstemp(dir=credentials.parent, prefix=".credentials-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write("\n".join(lines) + "\n")
        os.replace(temporary, credentials)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("Key saved. The ADS helper will reuse it automatically in this user account.")
    print("Credential presence was checked locally; the key has not been validated online.")


if __name__ == "__main__":
    main()
