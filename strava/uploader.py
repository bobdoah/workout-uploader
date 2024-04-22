#!/usr/bin/env python3
import argparse
import os

from collections import deque

from bs4 import BeautifulSoup
from stravalib.client import Client
from strava_client import get_authorized_client
from stravalib.exc import ActivityUploadFailed


def is_read_rate_limit_exceeded(err: Exception) -> bool:
    if not isinstance(err, ActivityUploadFailed) or not isinstance(err.args, list):
        return False
    error_response = err.args[0]
    return (
        isinstance(error_response, dict)
        and error_response.get("field") == "read rate limit"
        and error_response.get("code") == "exceeded"
    )


def get_activity_id_from_error(err: str) -> int:
    a = BeautifulSoup(err).a
    if a is None:
        raise Exception(f"Error string does not contain a link: {err}")
    href = str(a["href"])
    return int(href.split("/")[-1])


def get_gear_id(client: Client, bike: str) -> str:
    bikes = {b.name: b.id for b in client.get_athlete().bikes or []}
    if not bikes:
        raise Exception("No bikes found")
    gear_id = bikes[bike]
    if gear_id is None:
        raise Exception(f"No bike matching {bike} found")
    return gear_id


def main():
    p = argparse.ArgumentParser(description="Upload directory of activities to Strava")
    p.add_argument("files", type=argparse.FileType("r"))
    p.add_argument("-a", "--activity-type", choices=("ride", "run", "walk"))
    p.add_argument("-b", "--bike")
    p.add_argument("-c", "--commute", action=argparse.BooleanOptionalAction)
    args = p.parse_args()

    client = get_authorized_client()
    gear_id = get_gear_id(client, args.bike) if args.bike else None

    filenames = deque(args.files.readlines())
    while filenames:
        filename = filenames.popleft()
        filename = filename.strip()
        try:
            # Upload files, skipping duplicates
            _, ext = os.path.splitext(filename)
            print(f"uploading: {filename}")
            with open(filename, "rb") as filehandle:
                upload = client.upload_activity(
                    filehandle,
                    ext[1:],
                    commute=args.commute,
                    activity_type=args.activity_type,
                )
            try:
                activity = upload.wait()
                print(f"uploaded: http://strava.com/activities/{activity.id:d}")
                if not activity.id:
                    raise Exception(f"Activity does not have an id {activity}")
                activity_id = activity.id
            except ActivityUploadFailed as err:
                err_string = str(err)
                if "duplicate" not in err_string:
                    raise err
                activity_id = get_activity_id_from_error(err_string)
                print(
                    f"skipped duplicate of: http://strava.com/activities/{activity_id}"
                )
            # Set the bike, even if it's a duplicate upload
            if gear_id is not None:
                client.update_activity(activity_id=activity_id, gear_id=gear_id)  # type: ignore
                print(f"set gear to: {args.bike}")
        except Exception as err:
            # Retry the file if we catch an unhandleable exception
            filenames.appendleft(f"{filename}\n")
            if is_read_rate_limit_exceeded(err):
                print(f"retrying upload of {filename} due to read rate error")
                continue
            raise err
        finally:
            # Write out the list of remaining files
            with open(args.files.name, "w") as f:
                f.writelines(filenames)


if __name__ == "__main__":
    main()
