# ANSI Code Constants
RESET = "\033[0m"

# Text Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def print_header(h: str) -> None:
    print(f"[{h}]")


def print_step(s: str) -> None:
    print(f" > {s + ' ':.<70}", end='', flush=True)


def print_ok() -> None:
    print(f" {GREEN}OK{RESET}")


def print_failed(e: str) -> None:
    print(f" {RED}FAIL")
    print(f"! {e}{RESET}")


def print_warning(w: str) -> None:
    print(f" {YELLOW}{w}{RESET}")
