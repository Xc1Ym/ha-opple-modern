"""Light platform for the Opple integration."""

import logging
from typing import Any, override

import probatio

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    MAX_COLOR_TEMP_KELVIN,
    MIN_COLOR_TEMP_KELVIN,
)
from .coordinator import OppleConfigEntry, OppleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        probatio.Required(CONF_HOST): cv.string,
        probatio.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddConfigEntryEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import a legacy YAML platform entry into the visual config flow."""
    _LOGGER.warning(
        "The Opple YAML platform is deprecated and was imported into Devices & "
        "services; remove this Opple block from configuration.yaml after checking "
        "the imported entry"
    )
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_HOST: config[CONF_HOST], CONF_NAME: config[CONF_NAME]},
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OppleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one Opple light from a config entry."""
    async_add_entities([OppleLight(entry.runtime_data)])


class OppleLight(CoordinatorEntity[OppleDataUpdateCoordinator], LightEntity):
    """Representation of an Opple Wi-Fi light."""

    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_has_entity_name = True
    _attr_max_color_temp_kelvin = MAX_COLOR_TEMP_KELVIN
    _attr_min_color_temp_kelvin = MIN_COLOR_TEMP_KELVIN
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}

    def __init__(self, coordinator: OppleDataUpdateCoordinator) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator)
        state = coordinator.data
        entry = coordinator.config_entry
        self._attr_unique_id = state.legacy_unique_id
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, state.mac)},
            identifiers={(DOMAIN, state.mac)},
            manufacturer="Opple",
            model=state.device_name or "Wi-Fi light",
            name=entry.data.get(CONF_NAME, entry.title),
        )

    @property
    @override
    def is_on(self) -> bool:
        """Return whether the light is on."""
        return self.coordinator.data.is_on

    @property
    @override
    def brightness(self) -> int:
        """Return the current brightness."""
        return self.coordinator.data.brightness

    @property
    @override
    def color_temp_kelvin(self) -> int:
        """Return the current color temperature."""
        return self.coordinator.data.color_temp_kelvin

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light and apply optional attributes."""
        await self.coordinator.async_apply(
            power=True,
            brightness=kwargs.get(ATTR_BRIGHTNESS),
            color_temp_kelvin=kwargs.get(ATTR_COLOR_TEMP_KELVIN),
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_apply(power=False)
