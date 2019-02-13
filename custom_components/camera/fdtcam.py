"""
Support for IP Cameras.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.generic/
"""
import asyncio
import logging

import aiohttp
import async_timeout
import requests
from requests.auth import HTTPBasicAuth
import voluptuous as vol

from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT, ATTR_ENTITY_ID)
from homeassistant.exceptions import TemplateError
from homeassistant.components.camera import (
    PLATFORM_SCHEMA, DEFAULT_CONTENT_TYPE, Camera, DOMAIN)
from homeassistant.helpers import config_validation as cv
from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.helpers.service import extract_entity_ids

_LOGGER = logging.getLogger(__name__)


REQUIREMENTS = ['libpyfdtcam==1.0.4']


DEFAULT_NAME = 'FDT Camera'
DEFAULT_PORT = '80'

SERVICE_PTZ_PRESET = 'fdt_ptz_preset'
SERVICE_PTZ = 'fdt_ptz'

ATTR_PTZ_PRESET = 'preset'
ATTR_PAN = 'pan'
ATTR_TILT = 'tilt'

DIR_UP = "UP"
DIR_DOWN = "DOWN"
DIR_LEFT = "LEFT"
DIR_RIGHT = "RIGHT"
PTZ_NONE = "NONE"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
})

SERVICE_PTZ_PRESET_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_PTZ_PRESET): cv.string,
})

SERVICE_PTZ_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Optional(ATTR_PAN, default=None): cv.string,
    vol.Optional(ATTR_TILT, default=None): cv.string,
})

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up a generic IP Camera."""

    async def handle_ptz_preset(camera, call):
        """ Service for moving Camera to an PTZ Preset. """
        preset = call.data.get(ATTR_PTZ_PRESET)
        camera.goto_ptz_preset(preset)
        return True

    async def handle_ptz(camera, call):
        """ Service for Moving Camera. """
        pan = call.data.get(ATTR_PAN)
        tilt = call.data.get(ATTR_TILT)
        camera.perform_ptz(pan, tilt)
        return True

    hass.data[DOMAIN].async_register_entity_service(
        SERVICE_PTZ_PRESET, SERVICE_PTZ_PRESET_SCHEMA, handle_ptz_preset)

    hass.data[DOMAIN].async_register_entity_service(
        SERVICE_PTZ, SERVICE_PTZ_SCHEMA, handle_ptz)

    async_add_entities([FDTHass(hass, config)])

class FDTHass(Camera):
    """ Implementation of FDT Camera """

    def __init__(self, hass, device_info):
        """ Initialize FDT Camera """
        from libpyfdtcam import FDTCam


        super().__init__()
        self._host = device_info.get(CONF_HOST)
        self._username = device_info.get(CONF_USERNAME)
        self._password = device_info.get(CONF_PASSWORD)
        self._port = device_info.get(CONF_PORT)
        self._name = device_info.get(CONF_NAME)

        self._cam = FDTCam(self._host,
                               self._port,
                               self._username,
                               self._password)

    @property
    def name(self):
        """ Return Devicename. """
        return self._name

    async def async_camera_image(self):
        """ Get still image. """
        image = self._cam.get_snapshot()
        return image

    async def async_enable_motion_detection(self):
        """ Enable motion detection. """
        self._cam.motion_on()

    async def async_disable_motion_detection(self):
        """ Disable motion detection. """
        self._cam.motion_off()

    def perform_ptz(self, pan, tilt):
        """ Move Camera. """
        direction = self._pt_direction(pan, tilt)
        self._cam.ptz_control(direction, 31)

    def _pt_direction(self, pan, tilt):
        """ Helper Function for Construction of ptz-command. """
        p = "right" if pan == DIR_RIGHT else "left" if pan == DIR_LEFT else ""
        t = "up" if tilt == DIR_UP else "down" if tilt == DIR_DOWN else ""
        dir = t + p
        return dir

    def goto_ptz_preset(self, preset):
        """ Call an PTZ Preset """
        self._cam.ptz_preset(int(preset))

    @property
    def motion_detection_enabled(self):
        """ Get Status of Motiondetection """
        return self._cam.motion_detect_status
