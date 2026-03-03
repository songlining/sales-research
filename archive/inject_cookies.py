#!/usr/bin/env python3
# /// script
# dependencies = ["pycookiecheat", "pycryptodome", "cryptography"]
# ///
"""
Pre-loads LinkedIn cookies into the MCP Chrome SQLite database BEFORE Chrome starts.

MCP Chrome uses --remote-debugging-pipe (no TCP port), so CDP websocket injection
is not available. Chrome also only reads cookies from SQLite at startup — runtime
writes are invisible. This script writes properly encrypted cookies before Chrome
starts, so the session is authenticated on the first navigation.

Encryption:
  MCP Chrome launches with --use-mock-keychain --password-store=basic.
  Chrome uses PBKDF2("peanuts", salt="saltysalt", 1003 iters, 16 bytes)
  as the AES-128-CBC key and stores cookies as: b"v10" + AES-128-CBC(value).
  We replicate this exact scheme so Chrome can decrypt on startup.

Workflow:
  1. Quit Claude Desktop (stops MCP Chrome, releases SQLite lock)
  2. Run:  uv run .claude/skills/sales-research/inject_cookies.py
  3. Relaunch Claude Desktop (Chrome starts, reads the pre-loaded cookies)
  4. Navigate to Sales Navigator — already authenticated

Run with:  uv run inject_cookies.py
       or: .venv/bin/python inject_cookies.py  (after venv setup)
"""

import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import time

LINKEDIN_URL = "https://www.linkedin.com"
HTTP_ONLY_COOKIES = {"li_at", "liap", "li_mc", "li_rm"}

# Chrome profile to read cookies FROM (your real Chrome)
# Common values: "Default", "Profile 1", "Profile 2", etc.
# Named profiles (like "Work") map to numbered profiles internally.
# Find your profile by running: ls ~/Library/Application\ Support/Google/Chrome/
CHROME_PROFILE = "Work"  # Larry's main profile (display name from Local State)

# Chrome timestamp helpers (microseconds since 1601-01-01 UTC)
CHROME_EPOCH_DELTA = 11644473600  # seconds between 1601-01-01 and 1970-01-01


def to_chrome_ts(unix_ts: float) -> int:
    return int((unix_ts + CHROME_EPOCH_DELTA) * 1_000_000)


def far_future_ts() -> int:
    return to_chrome_ts(time.time() + 365 * 24 * 3600 * 2)  # ~2 years


# ── Encryption (mock keychain) ───────────────────────────────────────────────
# MCP Chrome is launched with --use-mock-keychain --password-store=basic.
# Chrome's OSCrypt on macOS with the mock keychain uses:
#   - password:    b"peanuts"   (Chromium MockAppleKeychain hard-coded value)
#   - salt:        b"saltysalt" (Chrome hard-coded)
#   - iterations:  1003
#   - key length:  16 bytes (AES-128)
#   - IV:          b" " * 16 (16 space chars)
#   - format:      b"v10" prefix + AES-128-CBC ciphertext

def _mock_aes_key() -> bytes:
    """Derive the AES-128 key Chrome uses with --use-mock-keychain."""
    return hashlib.pbkdf2_hmac("sha1", b"peanuts", b"saltysalt", 1003, dklen=16)


def _encrypt_v10(plaintext: str) -> bytes:
    """Encrypt a cookie value in Chrome's v10 AES-128-CBC format."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    key = _mock_aes_key()
    iv = b" " * 16
    cipher = AES.new(key, AES.MODE_CBC, IV=iv)
    return b"v10" + cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))


def _decrypt_v10(data: bytes) -> str:
    """Decrypt a v10 cookie value (for verify step)."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    key = _mock_aes_key()
    iv = b" " * 16
    cipher = AES.new(key, AES.MODE_CBC, IV=iv)
    return unpad(cipher.decrypt(data[3:]), AES.block_size).decode("utf-8")


# ── Step 1: Extract cookies from real Chrome ────────────────────────────────

def _get_local_state_names() -> dict[str, tuple[str, str]]:
    """
    Read Chrome's Local State file to get display names and emails for all profiles.
    Returns mapping: profile_dir_name -> (display_name, email)
    e.g., {"Default": ("Work", "larry.song@hashicorp.com")}
    """
    local_state = os.path.expanduser("~/Library/Application Support/Google/Chrome/Local State")
    if not os.path.exists(local_state):
        return {}

    try:
        import json
        with open(local_state, "r", encoding="utf-8") as f:
            data = json.load(f)

        info_cache = data.get("profile", {}).get("info_cache", {})
        profiles = {}
        for profile_key, info in info_cache.items():
            # Local State uses keys like "Default", "Profile 1", etc.
            name = info.get("name", "")
            user_name = info.get("user_name", "")  # This is the email
            if name:
                profiles[profile_key] = (name, user_name)
        return profiles
    except Exception:
        return {}


def _find_chrome_profile_dir(profile_name: str) -> str | None:
    """
    Find the Chrome profile directory for a given profile name.
    Handles both directory names ("Default", "Profile 1") and display names ("Work", "Lining").
    """
    chrome_base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    if not os.path.isdir(chrome_base):
        return None

    # Get display names from Local State (now returns tuples)
    local_state_profiles = _get_local_state_names()

    # Direct directory match first
    direct = os.path.join(chrome_base, profile_name)
    if os.path.isdir(direct):
        return direct

    # Search by display name from Local State
    for dir_name, (display_name, _email) in local_state_profiles.items():
        if display_name == profile_name:
            profile_dir = os.path.join(chrome_base, dir_name)
            if os.path.isdir(profile_dir):
                return profile_dir

    # Fallback: search Preferences file (older method)
    for entry in os.listdir(chrome_base):
        profile_dir = os.path.join(chrome_base, entry)
        prefs_file = os.path.join(profile_dir, "Preferences")
        if not os.path.isfile(prefs_file):
            continue

        try:
            import json
            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            if prefs.get("profile", {}).get("name") == profile_name:
                return profile_dir
        except Exception:
            continue

    return None


def extract_cookies() -> dict:
    # Try configured profile first, then prompt if not found
    profile_name = CHROME_PROFILE
    profile_dir = _find_chrome_profile_dir(profile_name)

    # If not found, list available and prompt user
    if not profile_dir:
        print(f"⚠️  Chrome profile '{profile_name}' not found.")
        chrome_base = os.path.expanduser("~/Library/Application Support/Google/Chrome")

        if os.path.isdir(chrome_base):
            # Get display names from Local State (the authoritative source)
            local_state_profiles = _get_local_state_names()

            # Find all profiles with their display names
            profiles = []
            for entry in sorted(os.listdir(chrome_base)):
                profile_dir_path = os.path.join(chrome_base, entry)
                prefs_file = os.path.join(profile_dir_path, "Preferences")
                if not os.path.isfile(prefs_file):
                    continue

                # Use Local State display name + email if available
                if entry in local_state_profiles:
                    display_name, email = local_state_profiles[entry]
                    if email:
                        display = f"{display_name} ({email})"
                    else:
                        display = display_name
                else:
                    display = entry
                profiles.append((entry, display))

            if profiles:
                print("\n  Available Chrome profiles:")
                for path_name, display in profiles:
                    print(f"    - {display}")
                print()

                # Prompt user for profile
                while True:
                    response = input("Enter your Chrome profile name (or press Enter to use 'Default'): ").strip()
                    if not response:
                        profile_name = "Default"
                    else:
                        profile_name = response

                    profile_dir = _find_chrome_profile_dir(profile_name)
                    if profile_dir:
                        print(f"✓ Using profile: {profile_name}")
                        break
                    print(f"  Profile '{profile_name}' not found. Try again.")
            else:
                print("ERROR: No Chrome profiles found.")
                sys.exit(1)
        else:
            print("ERROR: Chrome data directory not found.")
            sys.exit(1)

    print(f"\nExtracting LinkedIn cookies from Chrome profile '{profile_name}'...")
    print(f"  Profile directory: {profile_dir}")

    try:
        from pycookiecheat import chrome_cookies
        raw = chrome_cookies(LINKEDIN_URL, browser="chrome", profile_dir=profile_dir)
    except Exception as e:
        print(f"ERROR: Failed to read Chrome cookies: {e}")
        sys.exit(1)

    if not raw:
        print(f"ERROR: No LinkedIn cookies found in profile '{CHROME_PROFILE}'.")
        print("  Log into LinkedIn in that Chrome profile first.")
        sys.exit(1)

    if "li_at" not in raw:
        print(f"ERROR: li_at cookie missing — LinkedIn session not active in profile '{CHROME_PROFILE}'.")
        print("  Log into LinkedIn in that Chrome profile.")
        sys.exit(1)

    print(f"  Extracted {len(raw)} cookies (li_at ✓, len={len(raw['li_at'])})")
    return raw


# ── Step 2: Find MCP Chrome profile ─────────────────────────────────────────

def find_mcp_chrome_profile() -> str | None:
    """
    Find MCP Chrome's user-data-dir from running processes, or fall back to
    the known default path used by chrome-devtools-mcp.
    """
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "chrome-devtools-mcp" in line and "user-data-dir" in line:
                m = re.search(r"--user-data-dir=(\S+)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass

    # Default path used by chrome-devtools-mcp when not overridden
    default = os.path.expanduser("~/.cache/chrome-devtools-mcp/chrome-profile")
    if os.path.isdir(default):
        return default

    return None


# ── Step 3: Write encrypted cookies to SQLite ───────────────────────────────

def _get_columns(conn: sqlite3.Connection) -> list[str]:
    return [row[1] for row in conn.execute("PRAGMA table_info(cookies)").fetchall()]


def sqlite_inject(raw_cookies: dict, profile_path: str) -> bool:
    cookie_db = os.path.join(profile_path, "Default", "Cookies")

    if not os.path.exists(cookie_db):
        print(f"  Cookie DB not found at: {cookie_db}")
        print("  Has claude-devtools-mcp been run at least once? (Creates the profile on first launch)")
        return False

    print(f"  Writing to: {cookie_db}")
    try:
        conn = sqlite3.connect(cookie_db, timeout=5)
        cols = _get_columns(conn)
        now = to_chrome_ts(time.time())
        expires = far_future_ts()
        injected = 0

        for name, value in raw_cookies.items():
            conn.execute(
                "DELETE FROM cookies WHERE host_key LIKE '%.linkedin.com' AND name = ?",
                (name,),
            )

            # Encrypt with mock keychain key (--use-mock-keychain uses "peanuts")
            enc_value = _encrypt_v10(value)

            row = {
                "creation_utc":       now + injected,  # must be unique per row
                "host_key":           ".linkedin.com",
                "name":               name,
                "value":              "",              # empty when encrypted_value is populated
                "encrypted_value":    enc_value,       # AES-128-CBC "v10" format
                "path":               "/",
                "expires_utc":        expires,
                "is_secure":          1,
                "is_httponly":        1 if name in HTTP_ONLY_COOKIES else 0,
                "last_access_utc":    now,
                "has_expires":        1,
                "is_persistent":      1,
                "priority":           1,
                "samesite":           -1,
                "source_scheme":      2,               # 2 = HTTPS
                "source_port":        443,
                "last_update_utc":    now,
                "source_type":        0,               # 0 = kUnknown
                "has_cross_site_ancestor": 0,
                "top_frame_site_key": "",
            }

            # Only insert columns that exist in this DB schema version
            valid = {k: v for k, v in row.items() if k in cols}
            placeholders = ", ".join("?" * len(valid))
            col_names = ", ".join(valid.keys())
            conn.execute(
                f"INSERT INTO cookies ({col_names}) VALUES ({placeholders})",
                list(valid.values()),
            )
            injected += 1

        conn.commit()
        conn.close()
        print(f"  Written {injected} cookies (encrypted with mock keychain key ✓)")
        return True

    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print("  SQLite locked — MCP Chrome is still running.")
            print("  ➜  Quit Claude Desktop first, then re-run this script.")
        else:
            print(f"  SQLite error: {e}")
        return False
    except Exception as e:
        print(f"  Unexpected error: {e}")
        return False


# ── Step 4: Verify roundtrip ─────────────────────────────────────────────────

def verify_roundtrip(raw_cookies: dict, profile_path: str) -> None:
    """Read li_at back from DB and decrypt to confirm encryption is correct."""
    try:
        cookie_db = os.path.join(profile_path, "Default", "Cookies")
        conn = sqlite3.connect(cookie_db, timeout=3)
        row = conn.execute(
            "SELECT encrypted_value FROM cookies "
            "WHERE host_key LIKE '%.linkedin.com' AND name = 'li_at' LIMIT 1"
        ).fetchone()
        conn.close()

        if not row or not row[0]:
            print("  Verify: li_at not found in DB after write — unexpected")
            return

        enc = bytes(row[0])
        if enc[:3] != b"v10":
            print(f"  Verify: unexpected prefix {enc[:3]!r}")
            return

        decrypted = _decrypt_v10(enc)
        expected = raw_cookies["li_at"]

        if decrypted == expected:
            print(f"  Verify: roundtrip decrypt ✓  (li_at len={len(decrypted)})")
        else:
            print(f"  Verify: MISMATCH — decrypted ({len(decrypted)}) != expected ({len(expected)})")

    except Exception as e:
        print(f"  Verify: could not check roundtrip: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    raw_cookies = extract_cookies()

    print("\nLocating MCP Chrome profile...")
    profile = find_mcp_chrome_profile()

    if not profile:
        print("ERROR: Could not find MCP Chrome profile.")
        print("  Expected: ~/.cache/chrome-devtools-mcp/chrome-profile")
        print("  Launch Claude Desktop once so the profile directory is created, then re-run.")
        sys.exit(1)

    print(f"  Profile: {profile}")

    # Warn if MCP Chrome is still running (SQLite will be locked)
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        chrome_running = any(
            "chrome-devtools-mcp" in line and "MacOS/Google Chrome" in line
            for line in result.stdout.splitlines()
        )
        if chrome_running:
            print("\n⚠️  MCP Chrome is RUNNING — SQLite may be locked.")
            print("   For the write to succeed AND for Chrome to see the cookies:")
            print("   1. Quit Claude Desktop")
            print("   2. Re-run this script")
            print("   3. Relaunch Claude Desktop\n")
    except Exception:
        pass

    if not sqlite_inject(raw_cookies, profile):
        sys.exit(1)

    verify_roundtrip(raw_cookies, profile)

    print("\n✅  Done.")
    print("   If Claude Desktop is running: quit and relaunch it now.")
    print("   Chrome will start with the injected cookies already loaded.")
    print("   Then navigate to: https://www.linkedin.com/sales/search/people")


if __name__ == "__main__":
    main()
