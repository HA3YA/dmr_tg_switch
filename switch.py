import logging
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.const import CONF_NAME

import requests
from requests.auth import HTTPBasicAuth
import json

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'dmr_tg_switch'

CONF_DMR_ID = 'dmr_id'
CONF_BM_API_KEY = 'bm_api_key'
CONF_TG = 'tg'
CONF_SLOT = 'tslot'

DEFAULT_NAME = 'DMR TG Switch'
DEFAULT_ICON = 'mdi:account-multiple'

URL_BM = "https://api.brandmeister.network/v1.0/repeater/"

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
        self._state = None
        self._is_on = False
        self.dmr_id: int = dmr_id
        self.bm_api_key: str = bm_api_key
        self.tg: int = tg
        self.tslot: int = tslot
        self._name: str = name
        self.update()
        
    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    #@property
    def turn_on(self, **kwargs):
        self._is_on = True
        # Send ADD command to BM
        url = URL_BM + "talkgroup/?action=ADD&id=" + str(self.dmr_id) 
        data = "talkgroup=" + str(self.tg) + "&timeslot=" + str(self.tslot)
        header = {'Content-Length': str(len(data)),
                  'Content-Type': 'application/x-www-form-urlencoded'
                 }
        response_api = requests.post(url, data=data, auth=HTTPBasicAuth(self.bm_api_key, ''), headers=header)         
        self.update()

    #@property
    def turn_off(self, **kwargs):
        self._is_on = False
        # Send DEL command to BM
        url = URL_BM + "talkgroup/?action=DEL&id=" + str(self.dmr_id) 
        data = "talkgroup=" + str(self.tg) + "&timeslot=" + str(self.tslot)
        header = {'Content-Length': str(len(data)),
                  'Content-Type': 'application/x-www-form-urlencoded'
                 }
        response_api = requests.post(url, data=data, auth=HTTPBasicAuth(self.bm_api_key, ''), headers=header)         
        self.update()
 
    def update(self):
        # Check BM 
        status = 0
        url = URL_BM + "?action=profile&q=" + str(self.dmr_id) 
        response_api = requests.get(url) 
        bm_data = json.loads(response_api.text)    
        for i in bm_data['staticSubscriptions']:
            if i["talkgroup"] == self.tg:
                self._is_on = True 
                status = 1
        if status == 0:
            self._is_on = False
  

