"""Config flow for the Opple integration."""

import ipaddress
from collections.abc import Mapping
from typing import Any, override

import probatio

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import CONF_ALLOW_OFFLINE, DEFAULT_NAME, DOMAIN, LOGGER
from .coordinator import (
    OppleConnectionError,
    OppleState,
    close_device,
    connect_device,
)


def _normalize_host(value: str) -> str:
    """Validate and normalize an IPv4 address."""
    return str(ipaddress.IPv4Address(value.strip()))


class OppleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Opple config flow."""

    VERSION = 2
    MINOR_VERSION = 0

    async def _async_validate(self, host: str) -> OppleState:
        """Connect to the light without retaining the temporary socket."""
        device = None
        try:
            device, state = await self.hass.async_add_executor_job(
                connect_device, host
            )
            return state
        finally:
            if device is not None:
                await self.hass.async_add_executor_job(close_device, device)

    @staticmethod
    def _schema(defaults: Mapping[str, Any] | None = None) -> probatio.Schema:
        """Return the visual configuration schema."""
        defaults = defaults or {}
        return probatio.Schema(
            {
                probatio.Required(
                    CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)
                ): TextSelector(TextSelectorConfig(autocomplete="off")),
                probatio.Required(
                    CONF_HOST, default=defaults.get(CONF_HOST, "")
                ): TextSelector(TextSelectorConfig(autocomplete="off")),
                probatio.Optional(
                    CONF_ALLOW_OFFLINE,
                    default=defaults.get(CONF_ALLOW_OFFLINE, False),
                ): bool,
            }
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                host = _normalize_host(user_input[CONF_HOST])
            except ipaddress.AddressValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                self._async_abort_entries_match({CONF_HOST: host})
                name = user_input[CONF_NAME].strip() or DEFAULT_NAME
                state: OppleState | None = None

                if not user_input[CONF_ALLOW_OFFLINE]:
                    try:
                        state = await self._async_validate(host)
                    except (OSError, OppleConnectionError):
                        errors["base"] = "cannot_connect"
                    except Exception:  # noqa: BLE001
                        LOGGER.exception("Unexpected exception validating Opple light")
                        errors["base"] = "unknown"

                if not errors:
                    unique_id = state.mac if state is not None else f"host:{host}"
                    await self.async_set_unique_id(unique_id, raise_on_progress=False)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=name,
                        data={CONF_HOST: host, CONF_NAME: name},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import one legacy YAML light platform entry."""
        try:
            host = _normalize_host(import_data[CONF_HOST])
        except ipaddress.AddressValueError:
            return self.async_abort(reason="invalid_host")

        self._async_abort_entries_match({CONF_HOST: host})
        name = str(import_data.get(CONF_NAME, DEFAULT_NAME)).strip() or DEFAULT_NAME
        await self.async_set_unique_id(f"host:{host}", raise_on_progress=False)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=name,
            data={CONF_HOST: host, CONF_NAME: name},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle visual reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                host = _normalize_host(user_input[CONF_HOST])
            except ipaddress.AddressValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                self._async_abort_entries_match({CONF_HOST: host})
                name = user_input[CONF_NAME].strip() or DEFAULT_NAME
                unique_id = entry.unique_id

                if not user_input[CONF_ALLOW_OFFLINE]:
                    try:
                        state = await self._async_validate(host)
                    except (OSError, OppleConnectionError):
                        errors["base"] = "cannot_connect"
                    except Exception:  # noqa: BLE001
                        LOGGER.exception("Unexpected exception validating Opple light")
                        errors["base"] = "unknown"
                    else:
                        if not str(entry.unique_id).startswith("host:"):
                            await self.async_set_unique_id(state.mac)
                            self._abort_if_unique_id_mismatch()
                        unique_id = state.mac

                if not errors:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=unique_id,
                        title=name,
                        data={CONF_HOST: host, CONF_NAME: name},
                    )

        defaults = {
            CONF_HOST: entry.data[CONF_HOST],
            CONF_NAME: entry.data.get(CONF_NAME, entry.title),
            CONF_ALLOW_OFFLINE: False,
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(user_input or defaults),
            errors=errors,
        )
