import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from familylink import FamilyLink
from familylink.models import AlwaysAllowedState


def main():
    parser = argparse.ArgumentParser(
        description="Apply Family Link configuration from CSV file"
    )
    parser.add_argument(
        "config_file",
        nargs="?",
        default="config.csv",
        help="Path to the configuration CSV file (default: config.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not apply changes, just print what would be done",
    )
    parser.add_argument(
        "--cookie-file",
        help="Path to the cookie file to use",
    )
    parser.add_argument(
        "--browser",
        choices=["firefox", "chrome"],
        default="firefox",
        help="Browser to use",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 80)
        print("Dry run mode enabled. No changes will be applied.")
        print("=" * 80)

    client_kwargs = {}

    if args.cookie_file:
        client_kwargs["cookie_file_path"] = Path(args.cookie_file)

    if args.browser:
        client_kwargs["browser"] = args.browser

    client = FamilyLink(**client_kwargs)

    if not Path(args.config_file).exists():
        _create_default_config(client, args.config_file)
        return

    config = _load_config(args.config_file)
    _apply_config(client, config, args.dry_run)


def _parse_duration(duration_str: str) -> int:
    """Convert duration string (H:MM) to minutes"""
    if not duration_str:
        return 0
    parts = duration_str.split(":")
    if len(parts) == 2:
        hours, minutes = map(int, parts)
        return hours * 60 + minutes
    return 0


def _parse_days(days_str: str) -> List[str]:
    """Convert day range (e.g., 'Mon-Wed' or 'Fri') to list of days"""
    if not days_str:
        return []

    days_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "fri": "friday",
        "sat": "saturday",
        "sun": "sunday",
    }

    all_days = list(days_map.values())
    if "-" in days_str:
        start, end = days_str.lower().split("-")
        start_idx = list(days_map.keys()).index(start)
        end_idx = list(days_map.keys()).index(end)
        selected_days = all_days[start_idx : end_idx + 1]
        return selected_days
    else:
        return [days_map[days_str.lower()]]


def _load_config(config_file="config.csv"):
    apps_config = {}

    with open(config_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            app = row["App"].strip()
            days = row["Days"].strip()
            time_ranges = row["Time Ranges"].strip()
            duration = row["Max Duration"].strip()

            # Handle always allowed apps (empty fields)
            if not any([days, time_ranges, duration]):
                apps_config[app] = {"always_allowed": True}
                continue

            if app not in apps_config:
                apps_config[app] = {"schedules": {}, "limits": {}}

            if not days:
                days = "mon-sun"

            if not time_ranges:
                time_ranges = "00:00-23:59"

            for day in _parse_days(days):
                if time_ranges:
                    apps_config[app]["schedules"][day] = time_ranges
                if duration:
                    apps_config[app]["limits"][day] = _parse_duration(duration)

    return apps_config


def _get_expected_limits(config: Dict) -> dict[str, bool | int]:
    expected_limits = dict[str, bool | int]()
    now = datetime.now()
    today = now.strftime("%A").lower()

    for app, settings in config.items():
        if settings.get("always_allowed"):
            expected_limits[app] = True
        elif limit := settings["limits"].get(today):
            if schedules := settings["schedules"].get(today):
                for schedule in schedules.split(";"):
                    start, end = schedule.split("-")
                    if start <= now.time().strftime("%H:%M") <= end:
                        expected_limits[app] = limit
                        break
            else:
                expected_limits[app] = limit
    return expected_limits


def _apply_config(client: FamilyLink, config: Dict, dry_run: bool = True):
    expected_limits = _get_expected_limits(config)

    app_usage = client.get_apps_and_usage()

    # {"Always allowed app": True, "Limited app": 120, "Blocked app": False,
    # "Unsupervised app": None}
    current_limit_per_app = dict[str, bool | int]()

    for app in app_usage.apps:
        if limit := app.supervision_setting.usage_limit:
            current_limit_per_app[app.title] = limit.daily_usage_limit_mins
        elif app.supervision_setting.hidden:
            current_limit_per_app[app.title] = False
        elif (
            app.supervision_setting.always_allowed_app_info
            and app.supervision_setting.always_allowed_app_info.always_allowed_state
            == AlwaysAllowedState.ENABLED
        ):
            current_limit_per_app[app.title] = True
        elif not any(
            app.package_name.startswith(prefix)
            for prefix in ["com.google", "com.android"]
        ):
            # Apps that are not supervised yet (recent installs for example)
            current_limit_per_app[app.title] = None

    for app, limit in current_limit_per_app.items():
        if expected_limit := expected_limits.get(app):
            # The app is expected to be with a limit or always allowed
            if expected_limit == limit:
                # print(f"- ('{app}' is already set to the expected limit)")
                pass
            elif expected_limit is True:
                print(f"- Setting '{app}' to unlimited")
                if not dry_run:
                    client.always_allow_app(app)
            else:
                print(f"- Setting '{app}' to {expected_limit} min (previously {limit})")
                if not dry_run:
                    client.set_app_limit(app, expected_limit)

        elif limit is not False:
            print(f"- Blocking '{app}' (previously {limit}).")
            if not dry_run:
                client.block_app(app)


def _create_default_config(client: FamilyLink, config_file: str):
    """Create a default config file with all apps and 0:00 limit"""
    app_usage = client.get_apps_and_usage()

    with open(config_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "App",
                "Max Duration",
                "Days",
                "Time Ranges",
            ],
        )
        writer.writeheader()
        for app in sorted(app_usage.apps, key=lambda x: x.title):
            writer.writerow(
                {
                    "App": app.title,
                    "Max Duration": "0:00",
                    "Days": "",
                    "Time Ranges": "",
                }
            )
    print(f"Created default config file at {config_file}")


if __name__ == "__main__":
    main()
