import asyncio
from contextlib import AsyncExitStack

import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .exceptions import PaulmannAuthenticationError
from .models import State
from .const import *

_LOGGER = logging.getLogger(__name__)


class Paulmann:
    """Main class for communicating with Paulmann BLE lights ."""

    def __init__(self, address, pwd):
        self._pwd = pwd
        self._address = address
        self._client: BleakClient | None = None
        self._client_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
    @property
    def connected(self):
        return not self._client is None and self._client.is_connected

    async def get_client(self) -> BLEDevice:
        async with self._lock:
            if not self._client or not self._client.is_connected:
                _LOGGER.debug("Connecting")
                try:
                    self._client = await self._client_stack.enter_async_context(BleakClient(self._address, timeout=30))
                    await self._authenticate()
                except asyncio.TimeoutError as exc:
                    _LOGGER.debug(exc)
                    _LOGGER.debug("Timeout on connect", exc_info=True)
                    raise asyncio.TimeoutError("Timeout on connect")
                except BleakError as exc:
                    _LOGGER.debug(exc)
                    _LOGGER.debug("Error on connect", exc_info=True)
                    raise asyncio.TimeoutError("Error on connect") from exc
            else:
                _LOGGER.debug("Connection reused")

    async def _authenticate (self):
        """ authenticate with the device, does not alter state of self """
        try:
            await self._client.write_gatt_char(UUID_PWD,
                                               bytearray(self._pwd, 'ascii'),
                                               response=True)
        except Exception as e:
            raise PaulmannAuthenticationError("Could not authenticate to the light using password")

    def disconnect(self):
        self._client.disconnect()
        self._device = None

    async def set_state(self, on:bool = None, brightness:int = None, color_temp_kelvin:int = None, **kwargs):
        """ set state of the Paulmann lights
        Parameters
        ----------
        on : bool
            whether the light is on or off
        brightness : int
            brigtness in range of 0 to 100, where 0 is least bright
        color_temp_kelvin : int
            color in Kelvin in the range of 2700 to 6500
        """
        await self.get_client()

        if on is not None:
            if on:
                await self._client.write_gatt_char(UUID_ONOFF, bytearray([0x01]))
            else:
                await self._client.write_gatt_char(UUID_ONOFF, bytearray([0x00]))

        if brightness is not None:
            if brightness > 100:
                brightness = 100
            elif brightness < 0:
                brightness = 0
            await self._client.write_gatt_char(UUID_BRIGHTNESS, brightness.to_bytes(1, "little"))

        if color_temp_kelvin is not None:
            if color_temp_kelvin > 6500:
                color_temp_kelvin = 6500
            elif color_temp_kelvin < 2700:
                color_temp_kelvin = 2700
            await self._client.write_gatt_char(UUID_COLOR, color_temp_kelvin.to_bytes(2, "little"))

    async def get_state(self)-> State:
        """ return full state of the light """
        await self.get_client()
        data = {
            UUID_SYSTEM_TIME: await self._client.read_gatt_char(UUID_SYSTEM_TIME),
            UUID_ONOFF: int.from_bytes(await self._client.read_gatt_char(UUID_ONOFF)) == 1,
            UUID_BRIGHTNESS: int.from_bytes(await self._client.read_gatt_char(UUID_BRIGHTNESS), 'little'),
            UUID_NAME: (await self._client.read_gatt_char(UUID_NAME)).decode('ascii').rstrip("\x00"),
            UUID_COLOR: int.from_bytes(await self._client.read_gatt_char(UUID_COLOR), 'little'),
            UUID_TIMER: await self._client.read_gatt_char(UUID_TIMER),
            UUID_WORKING_MODE: await self._client.read_gatt_char(UUID_WORKING_MODE),
            UUID_CONTROLLER_ENABLE: bool(await self._client.read_gatt_char(UUID_CONTROLLER_ENABLE)),
        }

        return State.from_dict(data)