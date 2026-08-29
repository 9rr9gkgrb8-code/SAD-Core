"""Friendly local launcher for the SAD + Forge Platform Alpha browser application."""

from getpass import getpass

from api import create_server
from auth import AuthService
from platform_v04_service import SadPlatform04Service


def ensure_owner(auth):
    if auth.has_owner():
        return
    print("First-time private owner setup")
    print("This account controls users and development approvals on this computer.")
    username = input("Owner username (letters, numbers, dot, dash, or underscore): ").strip()
    password = None
    for attempt in range(3):
        print("Password typing is hidden: no letters, dots, or cursor movement will appear.")
        candidate = getpass("Owner password (12+ characters, letters and numbers): ")
        confirmation = getpass("Confirm owner password (type the same password again): ")
        if candidate == confirmation:
            password = candidate
            break
        remaining = 2 - attempt
        print(f"Passwords did not match. Please try again ({remaining} attempts left).")
    if password is None:
        print("Owner setup stopped after three mismatches. No account was created.")
        return False
    approval = input("Create this local owner account? Type CREATE: ").strip()
    if approval.upper() != "CREATE":
        print("Owner setup was cancelled. No account was created.")
        return False
    try:
        auth.bootstrap_owner(username, password, explicitly_approved=True)
    except (ValueError, PermissionError) as error:
        print(f"Owner setup could not finish: {error}")
        return False
    print("Owner account created successfully.")
    return True


def main():
    auth = AuthService()
    if ensure_owner(auth) is False:
        return
    service = SadPlatform04Service(auth=auth)
    server = create_server(service=service)
    print(f"SAD + Forge Platform Alpha 0.4 is ready at http://127.0.0.1:{server.server_port}/")
    print("Keep this window open while using the application. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSAD + Forge stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
