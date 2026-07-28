"""Local-first, reviewable social campaign packaging."""

from .models import CampaignBundle, CampaignConfig, ConfigError, PlatformDraft
from .workflow import build_campaign, export_campaign, load_campaign

__version__ = "0.1.0"

__all__ = [
    "CampaignBundle",
    "CampaignConfig",
    "ConfigError",
    "PlatformDraft",
    "build_campaign",
    "export_campaign",
    "load_campaign",
]
