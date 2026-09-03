"""Non-interactive loopback launcher for hosted SAD deployments.

The reverse proxy/tunnel owns remote TLS exposure. SAD itself remains loopback-only.
Owner bootstrap must be completed explicitly before this launcher is used.
"""

from api import create_server
from auth import AuthService


def build_cloud_server(auth=None, port=8765):
    auth = auth or AuthService()
    if not auth.has_owner():
        raise RuntimeError("SAD cloud startup blocked: bootstrap an Owner account explicitly first.")
    return create_server(host="127.0.0.1", port=port, service=None)


def main():
    server = build_cloud_server()
    print(f"SAD + Forge hosted core ready on loopback http://127.0.0.1:{server.server_port}/")
    print("Remote access must terminate through the approved HTTPS/private gateway.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
