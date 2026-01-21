#!/usr/bin/env python3
import argparse
import os
import time

from collections import deque

from bs4 import BeautifulSoup
from stravalib.client import Client
from strava_client import get_authorized_client
from stravalib.exc import ActivityUploadFailed, RateLimitExceeded


def get_activity_id_from_error(err: str) -> int:
    a = BeautifulSoup(err).a
    if a is None:
        raise Exception(f"Error string does not contain a link: {err}")
    href = str(a["href"])
    return int(href.split("/")[-1])


def is_rate_limit_error(err: Exception) -> bool:
    """Check if the exception is a Strava rate limit error."""
    if isinstance(err, RateLimitExceeded):
        return True
    if isinstance(err, ActivityUploadFailed):
        # Check for rate limit in error args
        if hasattr(err, 'args') and err.args:
            error_response = err.args[0]
            if isinstance(error_response, dict):
                field = error_response.get("field", "")
                code = error_response.get("code", "")
                if "rate limit" in field.lower() and code == "exceeded":
                    return True
            elif isinstance(error_response, str):
                if "rate limit" in error_response.lower():
                    return True
    return False


def wait_with_backoff(attempt: int, base_wait: int = 60, max_wait: int = 900) -> int:
    """Calculate and perform exponential backoff wait.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_wait: Base wait time in seconds (default: 60s = 1 minute)
        max_wait: Maximum wait time in seconds (default: 900s = 15 minutes)

    Returns:
        The actual wait time used
    """
    wait_time = min(base_wait * (2 ** attempt), max_wait)
    print(f"Rate limit hit. Waiting {wait_time} seconds before retry (attempt {attempt + 1})...")
    time.sleep(wait_time)
    return wait_time


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
    p.add_argument("--config", default="strava.toml")
    p.add_argument(
        "--upload-delay",
        type=int,
        default=2,
        help="Delay in seconds between uploads to avoid rate limits (default: 2)",
    )
    p.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retries on rate limit before giving up (default: 5)",
    )
    args = p.parse_args()

    client = get_authorized_client(args.config)
    gear_id = get_gear_id(client, args.bike) if args.bike else None

    filenames = deque(args.files.readlines())
    rate_limit_retries = 0
    uploads_since_last_rate_limit = 0

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

            # Reset rate limit counter after successful upload
            uploads_since_last_rate_limit += 1
            if uploads_since_last_rate_limit >= 3:
                rate_limit_retries = 0
                uploads_since_last_rate_limit = 0

            # Delay between uploads to avoid hitting rate limits
            if filenames and args.upload_delay > 0:
                time.sleep(args.upload_delay)

        except Exception as err:
            # Check if this is a rate limit error
            if is_rate_limit_error(err):
                if rate_limit_retries >= args.max_retries:
                    print(f"Max rate limit retries ({args.max_retries}) exceeded. Saving state and exiting.")
                    filenames.appendleft(f"{filename}\n")
                    with open(args.files.name, "w") as f:
                        f.writelines(filenames)
                    raise err

                # Re-queue the file and wait with exponential backoff
                filenames.appendleft(f"{filename}\n")
                wait_with_backoff(rate_limit_retries)
                rate_limit_retries += 1
                uploads_since_last_rate_limit = 0
                continue

            # For non-rate-limit errors, save state and exit
            filenames.appendleft(f"{filename}\n")
            print(f"updating {args.files.name} with current list of files")
            with open(args.files.name, "w") as f:
                f.writelines(filenames)
            raise err


if __name__ == "__main__":
    main()
