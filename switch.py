# dmr_tg_switch
# Copyright (c) 2024 HA3YA
# Licensed under the MIT License – see the LICENSE file for details.

import logging
from homeassistant.helpers.entity import ToggleEntity
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME

import requests
import json

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'dmr_tg_switch'

CONF_DMR_ID = 'dmr_id'
CONF_BM_API_KEY = 'bm_api_key'
CONF_TG = 'tg'
CONF_SLOT = 'tslot'

DEFAULT_NAME = 'DMR TG Switch'
DEFAULT_ICON = 'mdi:account-multiple'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DMR_ID): cv.positive_int,
        vol.Required(CONF_BM_API_KEY): cv.string,
        vol.Required(CONF_TG): cv.positive_int,
        vol.Required(CONF_SLOT): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
    }
)

DROP_CUR_QSO = 9998  # TG for Drop Current QSO 
DROP_DYN_TGS = 9997  # TG for Drop All Dynamic TG    

URL_BM = "https://api.brandmeister.network/v2/device/"

def setup_platform(hass, config, add_devices, discovery_info=None):
    dmr_id = config.get(CONF_DMR_ID)
    bm_api_key = config.get(CONF_BM_API_KEY)
    tg = config.get(CONF_TG)
    tslot = config.get(CONF_SLOT)
    name = config.get(CONF_NAME)

    switch = DMRTalkgroupSwitch(dmr_id, bm_api_key, tg, tslot, name)
    add_devices([switch])


class DMRTalkgroupSwitch(ToggleEntity):
    def __init__(self, dmr_id: int, bm_api_key: str, tg: int, tslot: int, name: str):
        self._attr_name = name
        self._attr_is_on = False
        self.dmr_id = dmr_id
        self.bm_api_key = bm_api_key
        self.tg = tg
        self.tslot = tslot

        self.headers = {
            'Authorization': f'Bearer {self.bm_api_key}',
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        self.update()

    def get_headers(self):
        return self.headers

    def turn_on(self, **kwargs):
        try:
            if self.tg == DROP_CUR_QSO:
                url = f"{URL_BM}{self.dmr_id}/action/dropCallRoute/{self.tslot}"
                response = requests.get(url, headers=self.get_headers())

            elif self.tg == DROP_DYN_TGS:
                url = f"{URL_BM}{self.dmr_id}/action/dropDynamicGroups/{self.tslot}"
                response = requests.get(url, headers=self.get_headers())

            else:
                url = f"{URL_BM}{self.dmr_id}/talkgroup"
                data = json.dumps({'slot': self.tslot, 'group': self.tg})
                response = requests.post(url, headers=self.get_headers(), data=data)

            if response.status_code == 200:
                self._attr_is_on = True
                _LOGGER.info("Turned on TG%d on device %d, slot %d", self.tg, self.dmr_id, self.tslot)
            else:
                _LOGGER.warning("Failed to turn on TG%d on device %d", self.tg, self.dmr_id)

        except requests.RequestException as e:
            _LOGGER.error("Error in turn_on: %s", str(e))

    def turn_off(self, **kwargs):
        try:
            url = f"{URL_BM}{self.dmr_id}/talkgroup/{self.tslot}/{self.tg}"
            response = requests.delete(url, headers=self.get_headers())

            if response.status_code == 200:
                self._attr_is_on = False
                _LOGGER.info("Turned off TG%d on device %d, slot %d", self.tg, self.dmr_id, self.tslot)
            else:
                _LOGGER.warning("Failed to turn off TG%d on device %d", self.tg, self.dmr_id)

        except requests.RequestException as e:
            _LOGGER.error("Error in turn_off: %s", str(e))

    def update(self):
        try:
            url = f"{URL_BM}{self.dmr_id}/talkgroup"
            response = requests.get(url, headers=self.get_headers())

            if response.status_code == 200:
                bm_data = response.json()
                self._attr_is_on = any(i["talkgroup"] == str(self.tg) for i in bm_data)
                _LOGGER.info("Updated state for TG%d on device %d", self.tg, self.dmr_id)
            else:
                _LOGGER.warning("Failed to update state for TG%d on device %d", self.tg, self.dmr_id)

        except requests.RequestException as e:
            _LOGGER.error("Error in update: %s", str(e))
            
