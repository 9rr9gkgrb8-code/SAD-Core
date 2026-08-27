"""Friendly local launcher for the SAD + Forge Alpha 1 browser application."""

from getpass import getpass

from api import create_server
from auth import AuthService


def ensure_owner(auth):
    if auth.has_owner():
        return
    print("First-time private owner setup")
    print("This account controls users and development approvals on this computer.")
    username = input("Owner username: ").strip()
    password = getpass("Owner password (12+ characters, letters and numbers): ")
    confirmation = getpass("Confirm owner password: ")
    if password != confirmation:
        raise ValueError("Passwords did not match. No account was created.")
    approval = input("Create this local owner account? Type CREATE: ").strip()
    if approval != "CREATE":
        raise PermissionError("Owner setup was cancelled.")
    auth.bootstrap_owner(username, password, explicitly_approved=True)


def main():
    auth = AuthService()
    ensure_owner(auth)
    server = create_server(service=None)
    print(f"SAD + Forge Alpha 1 is ready at http://127.0.0.1:{server.server_port}/")
    print("Keep this window open while using the application. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSAD + Forge stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
