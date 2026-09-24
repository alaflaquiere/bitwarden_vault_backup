# Bitwarden Vault Backup

A small command-line tool that logs into your Bitwarden account via the official
`bw` CLI, exports your vault, and repackages it as a password-encrypted `.7z`
archive for safe offline storage.

## What it does

1. Checks that `bw` (Bitwarden CLI) and `7z` (7-Zip) are installed.
2. Checks whether an update to `bw` is available (informational only).
3. Prompts for your email, a backup folder, and your master password, then logs
   in and obtains a session key.
4. Syncs your vault.
5. Exports the vault to a temporary zip, extracts it, and re-compresses it into
   an encrypted `encrypted_vault_data.7z` file (protected with your master
   password) in the backup folder you chose.
6. Cleans up all intermediate files.
7. Locks and logs out of the `bw` session.

Your email and backup folder are cached locally (not your password) so you can
reuse them on the next run without retyping them.

## Prerequisites

- **Python 3.9+**
- **Bitwarden CLI (`bw`)** — install from the [official instructions](https://bitwarden.com/help/cli/#download-and-install). Verify with:
  ```bash
  bw --version
  ```
  (Note: this script was tested with version 2026.8.0 of Bitwarden CLI.)
- **7-Zip (`7z`)** — must be available on your `PATH`.
  - macOS: `brew install sevenzip` (or `brew install p7zip` depending on availability)
  - Debian/Ubuntu: `sudo apt install p7zip-full`
  - Windows: install [7-Zip](https://www.7-zip.org/) and ensure `7z.exe` is on your `PATH`

  Verify with:
  ```bash
  7z -h
  ```

## Installation

Clone or download this project, then install it from the project root (the
folder containing `pyproject.toml`):

```bash
pip install .
```

For local development, where changes to the source are picked up
automatically:

```bash
pip install -e .
```


## Usage

Once installed, simply run:

```bash
bitwarden_vault_backup
```

You'll be prompted for:

- **Email address** — your Bitwarden account email (cached after first run).
- **Backup location** — a folder where the encrypted archive will be saved
  (cached after first run; created automatically if it doesn't exist).
- **Master password** — never cached; used to log in and to encrypt the final
  archive.

If login fails, the tool retries up to 3 times before giving up.

On success, you'll find `encrypted_vault_data.7z` in your chosen backup
folder. To extract it later, you'll need `7z` and the same master password
you used to create it:

```bash
7z x encrypted_vault_data.7z -o<output_folder>
```

## Cached configuration

Your email and backup folder (not your password) are cached at:

```
~/.bitwarden_vault_backup_cache/cached_login_config.json
```

Delete this file if you want to clear the cached values.

## Security notes

- Your master password is passed as a command-line argument to `bw` and `7z`
  subprocesses. On most systems, command-line arguments of running processes
  can be visible to other local users/processes (e.g. via `ps`), so only run
  this tool on machines you trust.
- The final `.7z` archive is encrypted (including file names, via `-mhe=on`)
  with your master password — keep that password safe, since it's required
  to both unlock your vault and open the backup archive.
- The tool logs out (`bw logout`) and locks the session at the end of a run.

## Troubleshooting

- **"Checking bw-cli and 7z installations" fails** — make sure both `bw` and
  `7z` are installed and available on your `PATH`, then re-open your
  terminal.
- **Invalid backup location** — the path must be a valid, writable directory
  (it will be created if missing, but it cannot point to an existing file).
- **Login keeps failing** — double-check your email/master password, and
  confirm you don't have 2FA-only login restrictions that this tool doesn't
  support (`bw login` is called with `--method 0`, i.e. authenticator-app
  method is not used here — see `bw login --help` for other methods if
  needed).