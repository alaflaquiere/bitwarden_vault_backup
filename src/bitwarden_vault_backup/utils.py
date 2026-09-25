import getpass
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bitwarden_vault_backup.print_utils import *

CACHE_DIR = Path.home() / ".bitwarden_vault_backup_cache"
CACHE_FILE = CACHE_DIR / "cached_login_config.json"
ZIP_NAME = "vault_data.zip"
TEMP_NAME = "temp_data"
ENCRYPTED_NAME = "encrypted_vault_data.7z"


@dataclass
class LoginConfig:
    user_email: str = ''
    pwd: str = ''
    save_folder: Path = Path()
    session_key: str = ""


def sub_run(command: list[str], env: None | dict = None, input: None | str = None):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
        input=input,
    )


def check_installs() -> bool:
    print_step("Checking bw-cli and 7z installations")
    r = sub_run(["bw", "--version"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    r = sub_run(["7z", "-h"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    print_ok()
    return True


def check_for_update() -> bool:
    print_step("Checking for update")
    r = sub_run(["bw", "update"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    print_ok()
    if r.stdout.strip() != "No update available.":
        print_warning("Note: A bw-cli update is available; try 'bw update' for more instructions.")
    return True


def validate_path(p: str) -> bool:
    """
    Checks if a folder path is valid, creates it if missing,
    and verifies that files can be written inside it.
    """
    try:
        if not p.strip():
            return False
        # Get the absolute path
        path = Path(p).resolve()
        # Ensure this is not a file
        if not path.is_dir():
            return False
        # Create the folder
        path.mkdir(parents=True, exist_ok=True)
        # Check OS write permissions
        return os.access(path, os.W_OK)
    except (ValueError, TypeError, OSError):
        # Catches any error (bad characters, invalid syntax, system-level blocks...)
        return False


def load_login_conf_from_cache() -> tuple[str, str]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                conf_json = json.load(f)
            user_email_cached = conf_json["user_email"]
            save_folder_cached = conf_json["save_folder"]
            return user_email_cached, save_folder_cached
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, PermissionError, OSError):
            print_warning("(Error while trying to load config from cache.)")
    return "", ""


def collect_user_inputs() -> tuple[bool, LoginConfig]:
    # Load conf from cache
    user_email_cached, save_folder_cached = load_login_conf_from_cache()

    # Modify prompt is conf loaded from cache
    extra = " (leave empty to use cached config)" if user_email_cached else ""
    # Get user input
    user_email = input(f"    Enter your email address{extra}: ")
    # Use cached if empty input
    if not user_email and user_email_cached:
        user_email = user_email_cached
        print(f"\033[1A\033[K    Enter your email address{extra}: {green(user_email)}", flush=True)

    # Modify prompt is conf loaded from cache
    extra = " (leave empty to use cached config)" if save_folder_cached else ""
    # Get user input
    save_folder_raw = input(f"    Enter backup location{extra}: ")
    # Use cached if empty input
    if not save_folder_raw and save_folder_cached:
        save_folder_raw = save_folder_cached
        print(f"\033[1A\033[K    Enter backup location{extra}: {green(save_folder_raw)}", flush=True)

    # Check the validity of the provided path
    if not validate_path(save_folder_raw):
        print(red("     Invalid backup location."))
        return False, LoginConfig()

    # Get master password
    pwd = getpass.getpass("    Enter your master password: ")

    return True, LoginConfig(user_email=user_email, pwd=pwd, save_folder=Path(save_folder_raw))


def cache_inputs(conf: LoginConfig) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"user_email": conf.user_email, "save_folder": str(conf.save_folder)}, f)
    except (AttributeError, TypeError, PermissionError, FileNotFoundError, OSError):
        print_warning("(Error while trying to save config to cache.)")


def get_session_key(conf: LoginConfig) -> bool:
    print_step("Logging in new session")

    # Make sure any previous session is closed
    r = sub_run(["bw", "logout"])
    if r.returncode != 0 and r.stderr != "You are not logged in.":
        print_failed(f"Error while logging out of previous session: {r.stderr}")
        return False

    # Save the password to an environment variable to avoid exposing it in the command line
    env = os.environ.copy()
    env["BW_PASSWORD"] = conf.pwd

    # Log in
    r = sub_run(["bw", "login", conf.user_email, "--passwordenv", "BW_PASSWORD", "--method", "0"], env=env)
    if r.returncode != 0:
        print_failed(f"Error while logging: {r.stderr}")
        return False

    # Extract the session key
    match = re.search(r'export BW_SESSION="([^"]+)"', r.stdout)
    if match == None:
        print_failed("Error while logging: Could not obtain a session key.")
        return False
    conf.session_key = match.group(1)
    print_ok()
    return True


def sync_vault() -> bool:
    print_step("Synchronizing the vault")
    r = sub_run(["bw", "sync"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    print_ok()
    return True


def clean_up(p: Path) -> None:
    if p.exists():
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            else:
                raise ValueError("Error in type of path.")
        except (FileNotFoundError, OSError, PermissionError):
            print(red(f" /!\\ UNABLE TO DELETE '{p}'; MAKE SURE TO MANUALLY DELETE IT"))
            input(" Press Enter to continue.")


def export_vault_data(conf: LoginConfig) -> bool:
    print_step("Exporting encrypted vault")

    zip_path = conf.save_folder / ZIP_NAME
    temp_folder = conf.save_folder / TEMP_NAME
    encrypted_zip_path = conf.save_folder / ENCRYPTED_NAME

    clean_up(zip_path)
    r = sub_run(["bw", "export", "--output", str(zip_path), "--format", "zip", "--session", conf.session_key])
    if r.returncode != 0:
        print_failed(f"Failed to export the data: {r.stderr}")
        clean_up(zip_path)
        return False

    # Extract the data from the zip file
    clean_up(temp_folder)
    r = sub_run(["7z", "x", str(zip_path), f"-o{temp_folder}"])
    if r.returncode != 0:
        print_failed(f"Failed to process the vault data: {r.stderr}")
        clean_up(zip_path)
        clean_up(temp_folder)
        return False

    # Create an encrypted zip file
    clean_up(encrypted_zip_path)
    r = sub_run(
        ["7z", "a", "-t7z", "-mx=9", "-mhe=on", "-y", "-p", str(encrypted_zip_path), f"{temp_folder}/*"],
        input=conf.pwd + "\n",
    )
    if r.returncode != 0:
        print_failed(f"Failed to build encrypted archive: {r.stderr}")
        clean_up(zip_path)
        clean_up(temp_folder)
        return False

    print_ok()
    clean_up(zip_path)
    clean_up(temp_folder)
    return True


def close_session() -> bool:
    print_step("Closing session")
    r = sub_run(["bw", "lock"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    r = sub_run(["bw", "logout"])
    if r.returncode != 0:
        print_failed(r.stderr)
        return False
    print_ok()
    return True
