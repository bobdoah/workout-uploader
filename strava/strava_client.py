from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import time
import tomllib
import tomli_w
import stravalib
import webbrowser


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.received = parse_qs(self.path.split("?", 1)[1])
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"""<html>
            <head><title>Strava auth code received</title></head>
            <body><p>This window can be closed</p></body>
            </html>"""
        )


class TokenHandler(HTTPServer):
    def __init__(self, port):
        self.received = None
        HTTPServer.__init__(self, ("localhost", port), handler)


def get_client_config(
    client_config: str,
) -> tuple[int, str, str | None, str | None, int | None]:
    with open(client_config, "rb") as f:
        data = tomllib.load(f)
    return (
        data["client_id"],
        data["client_secret"],
        data.get("access_token"),
        data.get("refresh_token"),
        data.get("expires_at"),
    )


def write_client_config(
    client_config: str,
    client_id: int,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    expires_at: int,
):
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }
    with open(client_config, "wb") as f:
        tomli_w.dump(data, f)


def get_authorized_client(client_config: str) -> stravalib.Client:
    client_id, client_secret, access_token, refresh_token, expires_at = (
        get_client_config(client_config)
    )
    if not access_token or not refresh_token or not expires_at:
        access_token, refresh_token, expires_at = authorize(client_id, client_secret)
        write_client_config(
            client_config,
            client_id,
            client_secret,
            access_token,
            refresh_token,
            expires_at,
        )

    client = stravalib.Client(access_token)

    if time.time() > expires_at:
        access_info = client.refresh_access_token(
            client_id, client_secret, refresh_token
        )
        write_client_config(
            client_id,
            client_secret,
            access_info["access_token"],
            access_info["refresh_token"],
            access_info["expires_at"],
        )
    return client


def authorize(client_id: int, client_secret: str) -> tuple[str, str, int]:
    client = stravalib.client.Client()
    port = 8080
    th = TokenHandler(port)
    authorize_url = client.authorization_url(
        client_id=client_id,
        redirect_uri=f"http://localhost:{port}",
        scope=["profile:read_all", "activity:read_all", "activity:write"],
    )
    webbrowser.open_new_tab(authorize_url)
    th.handle_request()
    access_info = client.exchange_code_for_token(
        client_id=client_id, client_secret=client_secret, code=th.received["code"]
    )
    return (
        access_info["access_token"],
        access_info["refresh_token"],
        access_info["expires_at"],
    )
