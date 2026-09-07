"""Non-interactive loopback launcher for hosted SAD + Forge deployments.

The reverse proxy/tunnel owns remote TLS exposure. SAD itself remains loopback-only.
Owner bootstrap must be completed explicitly before this launcher is used.
"""

from api import create_server
from auth import AuthService
from signup_service import SignupSadApiService


def build_cloud_server(auth=None, port=8765):
    auth = auth or AuthService()
    if not auth.has_owner():
        raise RuntimeError("SAD cloud startup blocked: bootstrap an Owner account explicitly first.")
    service = SignupSadApiService(auth=auth)
    return create_server(host="127.0.0.1", port=port, service=service)


def main():
    server = build_cloud_server()
    print(f"SAD + Forge hosted core ready on loopback http://127.0.0.1:{server.server_port}/")
    print("Invite-only student signup is enabled; anonymous role selection remains disabled.")
    print("Remote access must terminate through the approved HTTPS/private gateway.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
