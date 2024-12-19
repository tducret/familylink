from enum import Enum
from typing import List, Optional

from pydantic.v1 import BaseModel, Field


# === Apps ===
class AppSupervisionCapability(str, Enum):
    """Supervision capabilities for an app."""

    ALWAYS_ALLOW = "capabilityAlwaysAllowApp"
    BLOCK = "capabilityBlock"
    USAGE_LIMIT = "capabilityUsageLimit"


class AdSupportStatus(str, Enum):
    """Ad support status for an app."""

    NO_ADS = "noAds"
    ADS_SUPPORTED = "adsSupported"


class IAPSupportStatus(str, Enum):
    """In-app purchase support status for an app."""

    NO_IAP = "noIap"
    IAP_SUPPORTED = "iapSupported"


class AppSource(str, Enum):
    """Source of the app installation."""

    GOOGLE_PLAY = "googlePlay"
    UNKNOWN = "unknownAppSource"


class AlwaysAllowedState(str, Enum):
    """State of always-allowed setting for an app."""

    ENABLED = "alwaysAllowedStateEnabled"


class AlwaysAllowedAppInfo(BaseModel):
    """Information about always-allowed status of an app."""

    always_allowed_state: AlwaysAllowedState = Field(alias="alwaysAllowedState")


class UsageLimit(BaseModel):
    """Usage limit settings for an app."""

    daily_usage_limit_mins: int = Field(alias="dailyUsageLimitMins")
    enabled: bool


class SupervisionSetting(BaseModel):
    """Supervision settings for an app."""

    hidden: bool = False
    hidden_set_explicitly: bool = Field(False, alias="hiddenSetExplicitly")
    hidden_on_dumbledore_flow: Optional[bool] = Field(
        None, alias="hiddenOnDumbledoreFlow"
    )
    usage_limit: Optional[UsageLimit] = Field(None, alias="usageLimit")
    always_allowed_app_info: Optional[AlwaysAllowedAppInfo] = Field(
        None, alias="alwaysAllowedAppInfo"
    )
    google_search_disabled: Optional[bool] = Field(None, alias="googleSearchDisabled")
    hidden_state_locked: Optional[bool] = Field(None, alias="hiddenStateLocked")


class App(BaseModel):
    """Information about an app."""

    package_name: str = Field(alias="packageName")
    title: str
    icon_url: str = Field(alias="iconUrl")
    supervision_setting: SupervisionSetting = Field(alias="supervisionSetting")
    install_time_millis: str = Field(alias="installTimeMillis")
    enforced_enabled_status: str = Field(alias="enforcedEnabledStatus")
    app_source: AppSource = Field(alias="appSource")
    supervision_capabilities: List[AppSupervisionCapability] = Field(
        alias="supervisionCapabilities"
    )
    ad_support_status: AdSupportStatus = Field(alias="adSupportStatus")
    device_ids: Optional[List[str]] = Field(default_factory=list, alias="deviceIds")
    iap_support_status: IAPSupportStatus = Field(alias="iapSupportStatus")


class AppId(BaseModel):
    """Identifier for an app."""

    android_app_package_name: str = Field(alias="androidAppPackageName")


class UsageDate(BaseModel):
    """Date information for app usage."""

    year: int
    month: int
    day: int


class AppUsageSession(BaseModel):
    """Usage session information for an app."""

    usage: str  # Duration in seconds with decimal places
    app_id: AppId = Field(alias="appId")
    device_mud_id: str = Field(alias="deviceMudId")
    mode_type: str = Field(alias="modeType")
    date: UsageDate


class DeviceDisplayInfo(BaseModel):
    """Display information for a device."""

    model: str
    friendly_name: str = Field(alias="friendlyName")
    last_activity_time_millis: str = Field(alias="lastActivityTimeMillis")


class DeviceCapabilityInfo(BaseModel):
    """Capability information for a device."""

    capabilities: List[str]


class DeviceInfo(BaseModel):
    """Information about a device."""

    device_id: str = Field(alias="deviceId")
    display_info: DeviceDisplayInfo = Field(alias="displayInfo")
    capability_info: DeviceCapabilityInfo = Field(alias="capabilityInfo")


class ApiHeader(BaseModel):
    """API response header."""

    server_timestamp_millis: str = Field(alias="serverTimestampMillis")


class AppUsage(BaseModel):
    """App usage response model."""

    api_header: ApiHeader = Field(alias="apiHeader")
    apps: List[App]
    last_activity_refresh_timestamp_millis: str = Field(
        alias="lastActivityRefreshTimestampMillis"
    )
    device_info: List[DeviceInfo] = Field(alias="deviceInfo")
    app_usage_sessions: List[AppUsageSession] = Field(alias="appUsageSessions")

    def get_app_title(self, package_name: str) -> str:
        """Get the title of an app."""
        for app in self.apps:
            if app.package_name == package_name:
                return app.title
        return "Unknown"


class Birthday(BaseModel):
    """Birthday information."""

    day: int
    month: int
    year: int


class Profile(BaseModel):
    """User profile information."""

    display_name: str = Field(alias="displayName")
    profile_image_url: str = Field(alias="profileImageUrl")
    email: str
    family_name: str = Field(alias="familyName")
    given_name: str = Field(alias="givenName")
    standard_gender: str = Field(alias="standardGender")
    birthday: Optional[Birthday] = None
    default_profile_image_url: str = Field(alias="defaultProfileImageUrl")


class MemberSupervisionInfo(BaseModel):
    """Supervision information for a member."""

    is_supervised_member: bool = Field(alias="isSupervisedMember")
    is_guardian_linked_account: bool = Field(alias="isGuardianLinkedAccount")


class MemberAttributes(BaseModel):
    """Member attributes."""

    show_parental_password_reset: Optional[bool] = Field(
        None, alias="showParentalPasswordReset"
    )


class UiCustomizations(BaseModel):
    """UI customization settings."""

    settings_group: List[str] = Field(alias="settingsGroup")
    privacy_policy_url: Optional[str] = Field(None, alias="privacyPolicyUrl")
    supervised_user_type: Optional[str] = Field(None, alias="supervisedUserType")


# === Members ===
class Member(BaseModel):
    """Member of the family."""

    user_id: str = Field(alias="userId")
    role: str
    profile: Profile
    state: str
    age_band_label: Optional[str] = Field(None, alias="ageBandLabel")
    member_supervision_info: Optional[MemberSupervisionInfo] = Field(
        None, alias="memberSupervisionInfo"
    )
    member_attributes: Optional[MemberAttributes] = Field(
        None, alias="memberAttributes"
    )
    ui_customizations: Optional[UiCustomizations] = Field(
        None, alias="uiCustomizations"
    )


class MembersResponse(BaseModel):
    """Response from the members API endpoint."""

    members: List[Member]
    api_header: ApiHeader = Field(alias="apiHeader")
    my_user_id: str = Field(alias="myUserId")
