"""Data update coordinator for the Opple integration."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import ParamSpec, TypeVar, override

from pyoppleio.OppleLightDevice import OppleLightDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, SCAN_INTERVAL

_P = ParamSpec("_P")
_R = TypeVar("_R")


class OppleConnectionError(Exception):
    """Raised when an Opple light cannot be reached."""


@dataclass(frozen=True, slots=True)
class OppleState:
    """A stable snapshot of an Opple light."""

    legacy_unique_id: str
    mac: str
    device_name: str
    is_on: bool
    brightness: int
    color_temp_kelvin: int


def _mac_from_device(device: OppleLightDevice) -> str:
    """Return a normalized MAC address from the library's raw octets."""
    if raw_mac := getattr(device, "mac_raw", None):
        return ":".join(f"{octet:02x}" for octet in raw_mac)
    compact = str(getattr(device, "mac", "")).replace(":", "").replace("-", "")
    if len(compact) != 12:
        raise OppleConnectionError("The device did not return a valid MAC address")
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2)).lower()


def snapshot_device(device: OppleLightDevice) -> OppleState:
    """Build a state snapshot or raise when the device is unavailable."""
    if not device.is_online:
        raise OppleConnectionError("The device is offline")

    mac = _mac_from_device(device)
    # Keep the exact legacy library value for the light entity unique ID so an
    # existing entity-registry record is reused during migration.
    legacy_unique_id = str(getattr(device, "mac", "")) or mac
    return OppleState(
        legacy_unique_id=legacy_unique_id,
        mac=mac,
        device_name=str(getattr(device, "name", "")),
        is_on=bool(device.power_on),
        brightness=int(device.brightness),
        color_temp_kelvin=int(device.color_temperature),
    )


def connect_device(host: str) -> tuple[OppleLightDevice, OppleState]:
    """Connect to a light and return its client and initial state."""
    device = OppleLightDevice(host)
    try:
        return device, snapshot_device(device)
    except Exception:
        close_device(device)
        raise


def close_device(device: OppleLightDevice) -> None:
    """Close the UDP socket owned by the legacy library."""
    socket = getattr(device, "socket", None)
    if socket is not None:
        socket.close()


def _update_device(device: OppleLightDevice) -> OppleState:
    """Refresh a device synchronously."""
    device.update()
    return snapshot_device(device)


def _apply_device_update(
    device: OppleLightDevice,
    *,
    power: bool | None,
    brightness: int | None,
    color_temp_kelvin: int | None,
) -> OppleState:
    """Apply requested values and return the library's read-back state."""
    if power is not None:
        device.power_on = power
    if brightness is not None:
        device.brightness = brightness
    if color_temp_kelvin is not None:
        device.color_temperature = color_temp_kelvin
    state = snapshot_device(device)
    if power is not None and state.is_on != power:
        raise OppleConnectionError("The power command was not confirmed")
    if brightness is not None and state.brightness != brightness:
        raise OppleConnectionError("The brightness command was not confirmed")
    if (
        color_temp_kelvin is not None
        and state.color_temp_kelvin != color_temp_kelvin
    ):
        raise OppleConnectionError("The color temperature command was not confirmed")
    return state


type OppleConfigEntry = ConfigEntry["OppleDataUpdateCoordinator"]


class OppleDataUpdateCoordinator(DataUpdateCoordinator[OppleState]):
    """Coordinate polling and commands for one Opple light."""

    config_entry: OppleConfigEntry

    def __init__(self, hass: HomeAssistant, entry: OppleConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )
        self._device: OppleLightDevice | None = None
        self._request_lock = asyncio.Lock()

    async def _async_run(self, func: Callable[_P, _R], *args: _P.args) -> _R:
        """Run blocking protocol code in Home Assistant's executor."""
        return await self.hass.async_add_executor_job(func, *args)

    def _async_update_entry_identity(self, state: OppleState) -> None:
        """Promote a host-based imported entry to the device MAC identity."""
        if self.config_entry.unique_id == state.mac:
            return

        existing = self.hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, state.mac
        )
        if existing is not None and existing.entry_id != self.config_entry.entry_id:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="duplicate_device",
            )
        self.hass.config_entries.async_update_entry(
            self.config_entry, unique_id=state.mac
        )

    @override
    async def _async_update_data(self) -> OppleState:
        """Fetch the latest light state."""
        async with self._request_lock:
            try:
                if self._device is None:
                    self._device, state = await self._async_run(
                        connect_device, self.config_entry.data[CONF_HOST]
                    )
                else:
                    state = await self._async_run(_update_device, self._device)
            except (OSError, OppleConnectionError) as err:
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="cannot_connect",
                ) from err

        self._async_update_entry_identity(state)
        return state

    async def async_apply(
        self,
        *,
        power: bool | None = None,
        brightness: int | None = None,
        color_temp_kelvin: int | None = None,
    ) -> None:
        """Apply a command and publish the read-back state."""
        if self._device is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
            )

        async with self._request_lock:
            try:
                state = await self._async_run(
                    partial(
                        _apply_device_update,
                        self._device,
                        power=power,
                        brightness=brightness,
                        color_temp_kelvin=color_temp_kelvin,
                    ),
                )
            except (OSError, OppleConnectionError) as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="command_failed",
                ) from err

        self.async_set_updated_data(state)

    async def async_close(self) -> None:
        """Release the protocol socket."""
        async with self._request_lock:
            if self._device is not None:
                await self._async_run(close_device, self._device)
                self._device = None
