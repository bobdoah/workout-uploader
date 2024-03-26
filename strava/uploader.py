from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs


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
    def __init__(self, port=65500):
        self.received = None
        HTTPServer.__init__(self, ("localhost", port), handler)


def get_client_config():
    with open("strava.toml", "rb") as f:
        data = tomllib.load(f)
    return data["client_id"], data["client_secret"]


def get_tokens():
    client_id, client_secret = get_client_config()
    th = TokenHandler()
    authorize_url = stravalib.client.authorization_url(
        client_id=client_id,
        redirect_url=f"http://{th.server_address}",
        scope=["profile:read_all", "activity:read_all", "activity:write"],
    )
    webbrowser.open_new_tab(authorize_url)
    th.handle_request()
    token = stravalib.client.exchange_code_for_token(
        client_id=client_id, client_secret=client_secret, code=th.received["code"]
    )
    return token["access_token"], token["refresh_token"]
