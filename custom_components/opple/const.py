"""Constants for the Opple integration."""

from datetime import timedelta
import logging

from homeassistant.const import Platform

DOMAIN = "opple"
PLATFORMS = [Platform.LIGHT]

CONF_ALLOW_OFFLINE = "allow_offline"
DEFAULT_NAME = "Opple light"

MIN_COLOR_TEMP_KELVIN = 3000
MAX_COLOR_TEMP_KELVIN = 5700
SCAN_INTERVAL = timedelta(seconds=30)

LOGGER = logging.getLogger(__package__)
