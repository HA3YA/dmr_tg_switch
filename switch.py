# dmr_tg_switch
# Copyright (c) 2021 HA3YA
# Licensed under the MIT License – see the LICENSE file for details.

import json
import logging
import time
from typing import Any

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "dmr_tg_switch"

CONF_DMR_ID = "dmr_id"
CONF_BM_API_KEY = "bm_api_key"
CONF_TG = "tg"
CONF_SLOT = "tslot"

DEFAULT_NAME = "DMR TG Switch"
DEFAULT_ICON = "mdi:account-multiple"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DMR_ID): cv.positive_int,
        vol.Required(CONF_BM_API_KEY): cv.string,
        vol.Required(CONF_TG): cv.positive_int,
        vol.Required(CONF_SLOT): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

DROP_CUR_QSO = 9998  # TG for Drop Current QSO
DROP_DYN_TGS = 9997  # TG for Drop All Dynamic TG

URL_BM = "https://api.brandmeister.network/v2/device/"

# DMR ID alapú cache.
#
# Fontos:
# - A cache kulcsa a dmr_id.
# - Egy adott dmr_id /talkgroup listáját csak akkor kérdezzük le újra,
#   ha a Home Assistant poller meghívja az adott entity update() metódusát
#   és az előző sikeres lekérdezés óta legalább scan_interval idő eltelt.
# - A scan_interval értékét Home Assistant oldalról az update() hívások
#   ütemezése határozza meg. A komponens itt nem állít külön időzítőt.
#
# Példa:
#   25 switch ugyanazzal a dmr_id-vel:
#     az első update() kérdez a BM API-tól,
#     a többi 24 ugyanabból a cache-ből dolgozik.
_TALKGROUP_CACHE: dict[int, dict[str, Any]] = {}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the DMR talkgroup switch platform."""
    dmr_id = config.get(CONF_DMR_ID)
    bm_api_key = config.get(CONF_BM_API_KEY)
    tg = config.get(CONF_TG)
    tslot = config.get(CONF_SLOT)
    name = config.get(CONF_NAME)

    switch = DMRTalkgroupSwitch(dmr_id, bm_api_key, tg, tslot, name)
    add_devices([switch])


class DMRTalkgroupSwitch(ToggleEntity):
    """Switch entity for BrandMeister static talkgroup handling."""

    def __init__(self, dmr_id: int, bm_api_key: str, tg: int, tslot: int, name: str):
        """Initialize the switch.

        Nincs induláskori self.update() hívás.
        Így Home Assistant restartkor nem indul el azonnal minden switch API lekérdezése.
        """
        self._attr_name = name
        self._attr_is_on = False
        self._attr_icon = DEFAULT_ICON

        self.dmr_id = dmr_id
        self.bm_api_key = bm_api_key
        self.tg = tg
        self.tslot = tslot

        self.headers = {
            "Authorization": f"Bearer {self.bm_api_key}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_headers(self):
        """Return BM API headers."""
        return self.headers

    def turn_on(self, **kwargs):
        """Turn on a static talkgroup or execute a BM action."""
        try:
            if self.tg == DROP_CUR_QSO:
                url = f"{URL_BM}{self.dmr_id}/action/dropCallRoute/{self.tslot}"
                response = requests.get(url, headers=self.get_headers(), timeout=15)

            elif self.tg == DROP_DYN_TGS:
                url = f"{URL_BM}{self.dmr_id}/action/dropDynamicGroups/{self.tslot}"
                response = requests.get(url, headers=self.get_headers(), timeout=15)

            else:
                url = f"{URL_BM}{self.dmr_id}/talkgroup"
                data = json.dumps({"slot": self.tslot, "group": self.tg})
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    data=data,
                    timeout=15,
                )

            if response.status_code == 200:
                self._attr_is_on = True
                _LOGGER.info(
                    "Turned on TG%d on device %d, slot %d",
                    self.tg,
                    self.dmr_id,
                    self.tslot,
                )

                # A változtatás után a régi cache már nem megbízható.
                _invalidate_talkgroup_cache(self.dmr_id)

            else:
                _LOGGER.warning(
                    "Failed to turn on TG%d on device %d. HTTP status: %s",
                    self.tg,
                    self.dmr_id,
                    response.status_code,
                )

        except requests.RequestException as err:
            _LOGGER.error("Error in turn_on: %s", err)

    def turn_off(self, **kwargs):
        """Turn off a static talkgroup."""
        try:
            url = f"{URL_BM}{self.dmr_id}/talkgroup/{self.tslot}/{self.tg}"
            response = requests.delete(url, headers=self.get_headers(), timeout=15)

            if response.status_code == 200:
                self._attr_is_on = False
                _LOGGER.info(
                    "Turned off TG%d on device %d, slot %d",
                    self.tg,
                    self.dmr_id,
                    self.tslot,
                )

                # A változtatás után a régi cache már nem megbízható.
                _invalidate_talkgroup_cache(self.dmr_id)

            else:
                _LOGGER.warning(
                    "Failed to turn off TG%d on device %d. HTTP status: %s",
                    self.tg,
                    self.dmr_id,
                    response.status_code,
                )

        except requests.RequestException as err:
            _LOGGER.error("Error in turn_off: %s", err)

    def update(self):
        """Update switch state from the DMR ID based shared cache.

        A Home Assistant scan_interval hívja ezt a metódust.
        Azonos dmr_id esetén csak az első switch végez tényleges BM API GET hívást,
        a többi switch ugyanabból a cache-elt /talkgroup listából dolgozik.
        """
        try:
            bm_data = _get_talkgroups_for_dmr_id(self.dmr_id, self.get_headers())

            if bm_data is None:
                _LOGGER.warning(
                    "Failed to update state for TG%d on device %d",
                    self.tg,
                    self.dmr_id,
                )
                return

            self._attr_is_on = _talkgroup_is_static(bm_data, self.tg, self.tslot)

            _LOGGER.debug(
                "Updated state for TG%d on device %d, slot %d: %s",
                self.tg,
                self.dmr_id,
                self.tslot,
                self._attr_is_on,
            )

        except requests.RequestException as err:
            _LOGGER.error("Error in update: %s", err)


def _get_talkgroups_for_dmr_id(dmr_id: int, headers: dict[str, str]):
    """Return cached or freshly downloaded /talkgroup data for one DMR ID.

    A cache itt nem használ külön TTL-t.
    Ez szándékos: a frissítés gyakoriságát a Home Assistant scan_interval adja.
    Egy HA poll cikluson belül azonos dmr_id-hez csak egy tényleges GET történik.

    A gyakorlati cache-frissítési logika:
    - ha nincs cache az adott dmr_id-hez: GET /talkgroup
    - ha van cache, de ebben a poll ciklusban már frissült: cache visszaadása
    - ha a cache régi, de a HA újra meghívta az update()-et: az első entitás frissíti
    """
    now = time.monotonic()

    cached = _TALKGROUP_CACHE.get(dmr_id)

    # Ha már van frissített adat ehhez a dmr_id-hez, visszaadjuk.
    #
    # A 10 másodperces "poll window" célja, hogy amikor a HA egymás után
    # végighívja az azonos scan_interval szerint esedékes entitásokat,
    # akkor csak az első küldjön API kérést, a többi cache-ből dolgozzon.
    #
    # Maga a következő nagy frissítési ciklus továbbra is a scan_interval
    # szerint fog bekövetkezni, mert a HA csak akkor hívja újra az update()-et.
    if cached is not None and now - cached["updated_at"] < 10:
        return cached["data"]

    url = f"{URL_BM}{dmr_id}/talkgroup"

    _LOGGER.debug("Downloading BM talkgroup list for device %d", dmr_id)

    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code != 200:
        _LOGGER.warning(
            "Failed to download BM talkgroup list for device %d. HTTP status: %s",
            dmr_id,
            response.status_code,
        )

        # Ha van régebbi cache, inkább azt használjuk, mint hogy minden unknown/off legyen.
        if cached is not None:
            _LOGGER.warning(
                "Using stale cached BM talkgroup list for device %d",
                dmr_id,
            )
            return cached["data"]

        return None

    data = response.json()

    _TALKGROUP_CACHE[dmr_id] = {
        "updated_at": now,
        "data": data,
    }

    return data


def _invalidate_talkgroup_cache(dmr_id: int):
    """Invalidate cached BM talkgroup list for one DMR ID."""
    if dmr_id in _TALKGROUP_CACHE:
        del _TALKGROUP_CACHE[dmr_id]


def _talkgroup_is_static(bm_data, tg: int, tslot: int) -> bool:
    """Return True if the configured TG is in the BM static TG list.

    A korábbi kód csak a talkgroup mezőt nézte:
        any(i["talkgroup"] == str(self.tg) for i in bm_data)

    Itt megtartjuk ezt a kompatibilitást, de ha a BM válaszban van slot mező,
    akkor azt is figyelembe vesszük.
    """
    for item in bm_data:
        talkgroup = item.get("talkgroup")
        slot = item.get("slot")

        if str(talkgroup) != str(tg):
            continue

        # Ha a válasz nem tartalmaz slot mezőt, a régi működés szerint
        # csak TG alapján döntünk.
        if slot is None:
            return True

        if str(slot) == str(tslot):
            return True

    return False
    
    
