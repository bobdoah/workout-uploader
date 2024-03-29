import os
import argparse

from token_handler import get_authorized_client


def main():
    p = argparse.ArgumentParser(description="Upload directory of activities to Strava")
    p.add_argument("activities", nargs="*", type=argparse.FileType("rb"))
    p.add_argument("-a", "--activity-type", choices=("ride", "run", "walk"))
    p.add_argument("-b", "--bike")
    p.add_argument("-c", "--commute", action=argparse.BooleanOptionalAction)
    args = p.parse_args()

    client = get_authorized_client()
    for file in args.activities:
        _, ext = os.path.splitext(file.name)
        upload = client.upload_activity(file, ext[1:], commute=args.commute)
        activity = upload.wait()
        print(f"http://strava.com/activities/{reactivity.id:d}")


if __name__ == "__main__":
    main()
