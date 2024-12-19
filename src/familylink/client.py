import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import browser_cookie3
import httpx

from familylink.models import AlwaysAllowedState, AppUsage, MembersResponse


class FamilyLink:
    """Client to interact with Google Family Link."""

    BASE_URL = "https://kidsmanagement-pa.clients6.google.com/kidsmanagement/v1"
    ORIGIN = "https://familylink.google.com"

    def __init__(
        self,
        account_id: str | None = None,
        browser: str = "firefox",
        cookie_file_path: Path | None = None,
    ):
        """Initialize the Family Link client.

        Args:
            account_id: The Google account ID to manage
                (if not provided, the first supervised member is used)
            browser: The browser to get cookies from if sapisid not provided
            cookie_file_path: (Optional) The path to the cookie file to use
        """
        self.account_id = account_id

        cookie_kwargs = {}
        if cookie_file_path:
            if not cookie_file_path.exists():
                raise ValueError(f"Cookie file not found: {cookie_file_path}")
            if not cookie_file_path.is_file():
                raise ValueError(f"Cookie file is not a file: {cookie_file_path}")
            cookie_kwargs["cookie_file"] = str(cookie_file_path.resolve())

        self._cookies = getattr(browser_cookie3, browser)(**cookie_kwargs)

        for cookie in self._cookies:
            if cookie.name == "SAPISID" and cookie.domain == ".google.com":
                sapisid = cookie.value
                break

        if not sapisid:
            raise ValueError("Could not find SAPISID cookie in browser")

        # Generate authorization header
        sapisidhash = _generate_sapisidhash(sapisid, self.ORIGIN)
        authorization = f"SAPISIDHASH {sapisidhash}"

        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Origin": self.ORIGIN,
            "Content-Type": "application/json+protobuf",
            "X-Goog-Api-Key": "AIzaSyAQb1gupaJhY3CXQy2xmTwJMcjmot3M2hw",
            "Authorization": authorization,
        }
        self._session = httpx.Client(headers=self._headers, cookies=self._cookies)
        self._app_names = {}  # cache app names

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()

    def close(self):
        """Close the client session."""
        self._session.close()

    def get_members(self) -> MembersResponse:
        """Get members of the family."""
        response = self._session.get(
            f"{self.BASE_URL}/families/mine/members",
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return MembersResponse.validate(response.json())

    def get_apps_and_usage(self) -> AppUsage:
        """Get apps and usage data for the account."""
        params = {
            "capabilities": [
                "CAPABILITY_APP_USAGE_SESSION",
                "CAPABILITY_SUPERVISION_CAPABILITIES",
            ],
        }
        self._ensure_account_id()
        response = self._session.get(
            f"{self.BASE_URL}/people/{self.account_id}/appsandusage",
            headers={"Content-Type": "application/json"},
            params=params,
        )
        response.raise_for_status()
        app_usage = AppUsage.validate(response.json())
        self._cache_app_names(app_usage)
        return app_usage

    def update_app_restrictions(
        self,
        app_name: str,
        time_limit_minutes: Optional[int] = None,
        block: bool = False,
        always_allow: bool = False,
    ) -> dict:
        """Update restrictions for an app.

        Args:
            app_name: The Android app name (or package name)
            time_limit_minutes: Time limit in minutes (None to remove time limit)
            block: Whether to block the app entirely
            always_allow: Whether to always allow the app
        """
        if sum([bool(time_limit_minutes), block, always_allow]) > 1:
            raise ValueError(
                "Can only specify one of: time_limit_minutes, block, or always_allow"
            )

        package_name = self._get_app_package_name(app_name)

        if block:
            data = [[package_name], [1]]
        elif always_allow:
            data = [[package_name], None, None, [1]]
        elif time_limit_minutes is not None:
            data = [[package_name], None, [time_limit_minutes, 1]]
        else:
            raise ValueError(
                "Must specify one of: time_limit_minutes, block, or always_allow"
            )

        payload = json.dumps([self.account_id, [data]])

        response = self._session.post(
            f"{self.BASE_URL}/people/{self.account_id}/apps:updateRestrictions",
            content=payload,
        )
        response.raise_for_status()
        return response.json()

    def block_app(self, name: str):
        self.update_app_restrictions(name, block=True)

    def always_allow_app(self, name: str):
        self.update_app_restrictions(name, always_allow=True)

    def remove_app_limit(self, name: str):
        self.update_app_restrictions(name, time_limit_minutes=None)

    def set_app_limit(self, name: str, time_limit_minutes: int):
        self.update_app_restrictions(name, time_limit_minutes=time_limit_minutes)

    def print_usage(self):
        resp = self.get_apps_and_usage()

        print("-" * 30)
        print("Limited apps")
        print("-" * 30)

        for app in sorted(resp.apps, key=lambda x: x.title):
            if app.supervision_setting.usage_limit:
                print(
                    f"{app.title}: {app.supervision_setting.usage_limit.daily_usage_limit_mins} minutes"
                )

        print()
        print("-" * 30)
        print("Blocked apps")
        print("-" * 30)
        for app in sorted(resp.apps, key=lambda x: x.title):
            if app.supervision_setting.hidden:
                print(app.title)

        print()
        print("-" * 30)
        print("Always allowed apps")
        print("-" * 30)
        for app in sorted(resp.apps, key=lambda x: x.title):
            if app.supervision_setting.always_allowed_app_info and (
                app.supervision_setting.always_allowed_app_info.always_allowed_state
                == AlwaysAllowedState.ENABLED
            ):
                print(app.title)

        print()
        print("-" * 30)
        print("Usage per app (today)")
        print("-" * 30)

        today = datetime.now().date()
        today_usage = [
            app
            for app in resp.app_usage_sessions
            if (
                app.date.year == today.year
                and app.date.month == today.month
                and app.date.day == today.day
            )
        ]
        today_usage.sort(key=lambda x: float(x.usage.replace("s", "")), reverse=True)

        # Print sorted usage
        for app in today_usage:
            usage_seconds = float(app.usage.replace("s", ""))
            hours = int(usage_seconds // 3600)
            minutes = int((usage_seconds % 3600) // 60)
            seconds = int(usage_seconds % 60)

            app_title = resp.get_app_title(app.app_id.android_app_package_name)

            print(f"{app_title}: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _ensure_account_id(self):
        if not self.account_id:
            resp = self.get_members()
            for member in resp.members:
                if (
                    member.member_supervision_info
                    and member.member_supervision_info.is_supervised_member
                ):
                    self.account_id = member.user_id
                    break

        assert self.account_id, "Could not find supervised member"

    def _cache_app_names(self, resp: AppUsage):
        self._app_names = {app.title: app.package_name for app in resp.apps}

    def _get_app_package_name(self, name: str) -> str:
        """Get the Android package name for an app."""
        if not self._app_names:
            self.get_apps_and_usage()

        if name in self._app_names.values():
            # Already a package name
            return name

        for app_name, package_name in self._app_names.items():
            if name.lower() in app_name.lower():
                return package_name

        raise ValueError(f"Could not find package name for app: {name}")


def _generate_sapisidhash(sapisid: str, origin: str) -> str:
    """Generate the SAPISIDHASH token for Google API authorization.

    Args:
        sapisid: The SAPISID cookie value
        origin: The origin URL (e.g., 'https://familylink.google.com')

    Returns:
        The SAPISIDHASH string in the format: "{timestamp}_{sha1_hash}"
    """
    timestamp = int(time.time() * 1000)  # Current time in milliseconds
    to_hash = f"{timestamp} {sapisid} {origin}"
    sha1_hash = hashlib.sha1(to_hash.encode("utf-8")).hexdigest()
    return f"{timestamp}_{sha1_hash}"
