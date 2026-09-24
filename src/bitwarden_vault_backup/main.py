# Author: Alban Laflaquière
# Date: 12 September 2026

from bitwarden_vault_backup.print_utils import green, red
from bitwarden_vault_backup.utils import *


def main():
    print_header("BitWarden Vault Backup")

    # Check that expected tools are installed
    success = check_installs()
    if not success:
        print(red(" Failed to backup."))
        return

    # Check if bw-cli can be updated
    _ = check_for_update()

    # Login attempt (times 3)
    for _ in range(3):
        # Collect user inputs or read them from cache
        success, login_config = collect_user_inputs()
        if not success:
            continue
        # Login and get session key
        success = get_session_key(login_config)
        if not success:
            continue
        break
    if not success:
        print(red(" Failed to backup."))
        return

    # Cache user inputs for later re-use
    cache_inputs(login_config)

    # Sync the vault
    success = sync_vault()
    if not success:
        print(red(" Failed to backup."))
        return

    # Export vault data
    success = export_vault_data(login_config)
    if not success:
        print(red(" Failed to backup."))
        return

    # Close the session
    success = close_session()
    if not success:
        return

    print(green(" Backup successful."))


if __name__ == "__main__":
    main()
