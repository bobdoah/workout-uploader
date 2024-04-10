#!/usr/bin/env python3
import argparse
import os

from collections import deque

from bs4 import BeautifulSoup
from strava_client import get_authorized_client
from stravalib.exc import ActivityUploadFailed


def is_read_rate_limit_exceeded(err: ActivityUploadFailed) => bool:
    return (
        isinstance(err, list)
        and isinstance(err[0], dict)
        and err[0].get("field") == "read rate limit"
        and err[0].get("code") == "exceeded"
    )

def get_activity_id_from_error(err: string) => string:
    href = BeautifulSoup(err_string).a["href"]
    return href.split("/")[-1]

def main():
    p = argparse.ArgumentParser(description="Upload directory of activities to Strava")
    p.add_argument("activities", nargs="*", type=argparse.FileType("rb"))
    p.add_argument("-a", "--activity-type", choices=("ride", "run", "walk"))
    p.add_argument("-b", "--bike")
    p.add_argument("-c", "--commute", action=argparse.BooleanOptionalAction)
    args = p.parse_args()

    client = get_authorized_client()
    bikes = {b.name: b.id for b in client.get_athlete().bikes}
    gear_id = ""
    if args.bike:
        gear_id = bikes[args.bike]
    activities = deque(args.activities)
    while activities:
        file = activities.popleft()
        _, ext = os.path.splitext(file.name)
        try:
            upload = client.upload_activity(
                file, ext[1:], commute=args.commute, activity_type=args.activity_type
            )
            activity = upload.wait()
            print(f"uploaded: http://strava.com/activities/{activity.id:d}")
            activity_id = activity.id
        except ActivityUploadFailed as err:
            if is_read_rate_limit_exceeded(error):
                activities.append(file)
                continue
            err_string = str(err)
            if "duplicate" not in err_string:
                raise err
            activity_id = get_activity_id_from_error(err_string)
            print(f"skipped duplicate of: http://strava.com/activities/{activity_id}")
        if gear_id:
            client.update_activity(activity_id=activity_id, gear_id=gear_id)
            print(f"set gear to: {args.bike}")


if __name__ == "__main__":
    main()
