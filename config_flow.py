"""Config flow for GenericBT integration."""
from __future__ import annotations

import logging
from typing import Any

from bluetooth_data_tools import human_readable_name
import voluptuous as vol
from paulmann import PaulmannAuthenticationError

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.const import CONF_ADDRESS, CONF_PIN
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .paulmann.connector import Paulmann

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Generic BT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": human_readable_name(None, discovery_info.name, discovery_info.address)}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            local_name = discovery_info.name
            await self.async_set_unique_id(discovery_info.address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            device = Paulmann(discovery_info.device, user_input[CONF_PIN])
            try:
                await device.get_client()
            except PaulmannAuthenticationError as e:
                _LOGGER.exception(e)
                errors["base"] = "Could not authenticate to light"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=local_name,data={
                    CONF_ADDRESS: discovery_info.address,
                    CONF_PIN: user_input[CONF_PIN]
                })

        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery in async_discovered_service_info(self.hass):
                if (
                        discovery.address in current_addresses
                        or discovery.address in self._discovered_devices
                ):
                    continue
                self._discovered_devices[discovery.address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        service_info.address: (f"{service_info.name} ({service_info.address})")
                        for service_info in self._discovered_devices.values()
                    }
                ),
                vol.Required(CONF_PIN): str

            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

# """Config flow for paulmann_ble integration."""
# from __future__ import annotations
#
# import logging
# from typing import Any
#
# import voluptuous as vol
#
# from homeassistant import config_entries
# from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_MAC, CONF_PIN
# from homeassistant.core import HomeAssistant
# from homeassistant.data_entry_flow import FlowResult
# from homeassistant.exceptions import HomeAssistantError
#
# from paulmann import Paulmann
#
# from .const import DOMAIN
#
# _LOGGER = logging.getLogger(__name__)
#
# # TODO adjust the data schema to the data that you need
# STEP_USER_DATA_SCHEMA = vol.Schema(
#     {
#         vol.Required(CONF_MAC): str,
#         vol.Required(CONF_PIN): str,
#     }
# )
#
#
# async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
#     """Validate the user input allows us to connect.
#
#     Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
#     """
#     # TODO validate the data can be used to set up a connection.
#
#     # If your PyPI package is not built with async, pass your methods
#     # to the executor:
#     # await hass.async_add_executor_job(
#     #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
#     # )
#
#     # hub = PlaceholderHub(data[CONF_MAC], data[CONF_PIN])
#     device = Paulmann(data[CONF_MAC], data[CONF_PIN])
#     print(data)
#     state = await hass.async_add_executor_job(
#         retrieve_device_info,
#         device
#     )
#
#     if not state:
#         raise InvalidAuth
#     # If you cannot connect:
#     # throw CannotConnect
#     # If the authentication is wrong:
#     # InvalidAuth
#
#     # Return info that you want to store in the config entry.
#     return {"title": state.name, "mac": data[CONF_MAC], "pin": data[CONF_PIN]}
#
# def retrieve_device_info(device: Paulmann):
#     state = device.get_state()
#     device.disconnect()
#     return state
#
#
# class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
#     """Handle a config flow for paulmann_ble."""
#
#     VERSION = 1
#
#     async def async_step_user(
#         self, user_input: dict[str, Any] | None = None
#     ) -> FlowResult:
#         """Handle the initial step."""
#         errors: dict[str, str] = {}
#         if user_input is not None:
#             try:
#                 info = await validate_input(self.hass, user_input)
#             except CannotConnect:
#                 errors["base"] = "cannot_connect"
#             except InvalidAuth:
#                 errors["base"] = "invalid_auth"
#             except Exception:  # pylint: disable=broad-except
#                 _LOGGER.exception("Unexpected exception")
#                 errors["base"] = "unknown"
#             else:
#                 return self.async_create_entry(title=info["title"], data=user_input)
#
#         return self.async_show_form(
#             step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
#         )
#
#
#
# class CannotConnect(HomeAssistantError):
#     """Error to indicate we cannot connect."""
#
#
# class InvalidAuth(HomeAssistantError):
#     """Error to indicate there is invalid auth."""
