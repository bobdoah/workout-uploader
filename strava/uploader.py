from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import tomllib
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


def get_client_config():
    with open("strava.toml", "rb") as f:
        data = tomllib.load(f)
    return data["client_id"], data["client_secret"]


def get_tokens():
    client = stravalib.client.Client()
    client_id, client_secret = get_client_config()
    port = 8080
    th = TokenHandler(port)
    authorize_url = client.authorization_url(
        client_id=client_id,
        redirect_uri=f"http://localhost:{port}",
        scope=["profile:read_all", "activity:read_all", "activity:write"],
    )
    webbrowser.open_new_tab(authorize_url)
    th.handle_request()
    token = client.exchange_code_for_token(
        client_id=client_id, client_secret=client_secret, code=th.received["code"]
    )
    return token["access_token"], token["refresh_token"]
