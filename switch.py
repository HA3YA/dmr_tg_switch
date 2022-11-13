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
        vol.Optional(CONF_NAME, DEFAULT_NAME): cv.string
   }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    dmr_id = config.get(CONF_DMR_ID)
    bm_api_key = config.get(CONF_BM_API_KEY)
    tg = config.get(CONF_TG)
    tslot = config.get(CONF_SLOT)
    name = config.get(CONF_NAME)

    switch = DMRTalkgroupSwitch(dmr_id, bm_api_key, tg, tslot, name)

    add_devices([switch])

DROP_CUR_QSO = 9998         # TG for Drop Current QSO 
DROP_DYN_TGS = 9997         # TG for Drop All Dynamic TG    

URL_BM = "https://api.brandmeister.network/v2/device/"

class DMRTalkgroupSwitch(ToggleEntity):

    def __init__(self, dmr_id: int, bm_api_key: str, tg: int, tslot: int, name: str):
        self._state = None
        self._is_on = False
        self.dmr_id: int = dmr_id
        self.bm_api_key: str = bm_api_key
        self.tg: int = tg
        self.tslot: int = tslot
        self._name: str = name
        self.header_auth = {'Authorization': 'Bearer ' + self.bm_api_key}
        self.header_acpt = {'accept': 'application/json'}
        self.header_adel = {'accept': '*/*'}
        self.header_cont = {'Content-Type': 'application/json'}
        self.update()
        
    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    #@property
    def turn_on(self, **kwargs):
        if self.tg == DROP_CUR_QSO :
            url = URL_BM + str(self.dmr_id) + '/action/dropCallRoute/' + str(self.tslot)
            post_header = {}
            post_header.update(self.header_acpt)
            post_header.update(self.header_auth)
            response_api = requests.get(url, headers=post_header)
            if response_api.status_code == 200:
                _LOGGER.info('Dropped current QSO on %d device, slot %d', self.dmr_id, self.tslot)

        elif self.tg == DROP_DYN_TGS:
            url = URL_BM + str(self.dmr_id) + '/action/dropDynamicGroups/' + str(self.tslot)
            post_header = {}
            post_header.update(self.header_acpt)
            post_header.update(self.header_auth)
            response_api = requests.get(url, headers=post_header)
            if response_api.status_code == 200:
                _LOGGER.info('Dropped all Dynamic Groups on %d device, slot %d', self.dmr_id, self.tslot)

        else:
            url = URL_BM + str(self.dmr_id) + '/talkgroup' 
            post_header = {}
            post_header.update(self.header_acpt)
            post_header.update(self.header_auth)
            post_header.update(self.header_cont)
            post_data = {}
            post_data['slot'] = self.tslot
            post_data['group'] = self.tg
            response_api = requests.post(url, headers=post_header, data=json.dumps(post_data))
            if response_api.status_code == 200:
                self._is_on = True
                _LOGGER.info('Create a static talkgroup TG%d on %d device, slot %d', self.tg, self.dmr_id, self.tslot)
            else:
                _LOGGER.warning('Can\'t create a static talkgroup TG%d on %d device', self.tg, self.dmr_id)
        
    #@property
    def turn_off(self, **kwargs):
        url = URL_BM + str(self.dmr_id) + '/talkgroup/' + str(self.tslot) + '/' + str(self.tg)
        header = {}
        header.update(self.header_adel)
        header.update(self.header_auth)
        response_api = requests.delete(url, headers=header)
        if response_api.status_code == 200:
            self._is_on = False
            _LOGGER.info('Delete a static talkgroup TG%d on %d device, slot %d', self.tg, self.dmr_id, self.tslot)
        else:
            _LOGGER.warning('Can\'t delete a static talkgroup TG%d on %d device', self.tg, self.dmr_id)
    
    def update(self):
        status = 0
        url = URL_BM + str(self.dmr_id) + '/talkgroup'
        response_api = requests.get(url, headers=self.header_acpt) 
        response_api.encoding = 'utf-8'
        bm_data = response_api.json()
        if response_api.status_code == 200:
            for i in bm_data:
                if i["talkgroup"] == str(self.tg):
                    self._is_on = True 
                    status = 1
            if status == 0:
                self._is_on = False
            _LOGGER.info('Updated static talkgroup TG%d on %d device', self.tg, self.dmr_id)

