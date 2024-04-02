#!/usr/bin/env python3
import argparse
import garth
import tomllib
import requests
import http
import os

from garth.exc import GarthException

http.client.HTTPConnection.debuglevel = 5
requests.packages.urllib3.add_stderr_logger()


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
        print(f"upload result: {resp}")


# GET to activity-service/activity/status/1711913521944/<uuid>


if __name__ == "__main__":
    main()
