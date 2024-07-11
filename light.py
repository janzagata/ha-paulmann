"""Platform for light integration."""
from __future__ import annotations

import logging
from typing import Any

from .paulmann.connector import Paulmann

# Import the device class from the component that you want to support
from homeassistant.components.light import (LightEntity, ColorMode)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .paulmann.models import State

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config: ConfigEntry,
        add_entities: AddEntitiesCallback):
    add_entities([PaulmannLight(address=config.data['address'], pwd=config.data['pin'])])


class PaulmannLight(Paulmann, LightEntity):
    _attr_max_color_temp_kelvin = 6500
    _attr_min_color_temp_kelvin = 2700
    _attr_supported_color_modes = [
        ColorMode.BRIGHTNESS,
        ColorMode.COLOR_TEMP
    ]

    _state = None

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.async_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.set_state(True, **kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.set_state(False, **kwargs)

    @property
    def unique_id(self):
        return self._address

    @property
    def name(self):
        return self._state.name if self._state else ''

    @property
    def brightness(self):
        return round(self._state.brightness / 100 * 255) if self._state else None

    @property
    def color_temp_kelvin(self):
        return self._state.color if self._state else None

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state.on if self._state else False

    async def async_update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = State.from_dict(await self.get_state())