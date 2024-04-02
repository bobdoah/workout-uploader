#!/usr/bin/env python3
import argparse
import garth
import tomllib
import os
import time

from garth.exc import GarthException
from urllib.parse import urlparse


def session_config() -> str:
    return "~/.garth"


def client_config() -> str:
    return "garmin.toml"


def get_client_config() -> tuple[str, str]:
    with open(client_config(), "rb") as f:
        data = tomllib.load(f)
    return (data["username"], data["password"])


def authenticate():
    try:
        client = garth.resume(session_config())
        garth.client.username
        return client
    except (GarthException, FileNotFoundError):
        username, password = get_client_config()
        garth.login(username, password)
        garth.save(session_config())


def main():
    p = argparse.ArgumentParser(description="Upload directory of activities to Strava")
    p.add_argument("activities", nargs="*", type=argparse.FileType("rb"))
    p.add_argument("-a", "--activity-type", choices=("ride", "run", "walk"))
    p.add_argument("-b", "--bike")
    p.add_argument("-c", "--commute", action=argparse.BooleanOptionalAction)
    args = p.parse_args()

    authenticate()
    for file in args.activities:
        fname = os.path.basename(file.name)
        files = {"file": (fname, file)}
        resp = garth.client.post("connectapi", "/upload-service/upload", files=files)
        print(f"upload result: {resp.json()}")
        print(f"headers: {resp.headers}")
        location = resp.headers["location"]
        path = urlparse(location).path
        print(f"location: {location}, path: {path}")
        timeout = 600
        start = time.time()
        status
        result = {}
        while time.time() - start < timeout:
            resp = garth.client.get("connectapi", path)
            if resp.status_code >= 200 and resp.status_code < 300:
                result = resp.json()
                break
            time.sleep(10)


if __name__ == "__main__":
    main()
