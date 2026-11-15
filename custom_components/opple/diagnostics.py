"""Diagnostics support for the Opple integration."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import OppleConfigEntry

TO_REDACT = {CONF_HOST, "legacy_unique_id", "mac", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OppleConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": entry.runtime_data.last_update_success,
        "state": async_redact_data(asdict(entry.runtime_data.data), TO_REDACT),
    }
