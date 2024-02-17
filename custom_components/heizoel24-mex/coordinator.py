from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging
from .const import BASE_URL, LOGIN_SERVICE, DATA_SERVICE, DATA_SERVICE_SUFFIX, POLL_INTERVAL

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)



class MexUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="meX",
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )
        self.entry = entry
        self.session_id = None

    def login(self):
        _LOGGER.info('Login in...')
        REQ = { "Username" : self.entry.data["username"] ,
           "Password" : self.entry.data["password"] }
        _LOGGER.error(REQ)
        with requests.post(BASE_URL + LOGIN_SERVICE, json=REQ) as r:
            _LOGGER.error("Authenticating: %s", r.text)
            try:
                data = r.json()
            except json.JSONDecodeError as e:
                    if "login" in data.casefold():
                        raise ConfigEntryAuthFailed(data) from e
                    _LOGGER.error("E-sensorix API said: %s", data)

            if r.status_code == 200:
                _LOGGER.debug(r.text)
                if data['ResultCode'] == 0:
                    self.session_id = data['SessionId']
                    _LOGGER.info('Session ID: ' + self.session_id)
                    return
        # At this point not returned means there was an error
        _LOGGER.error("Heizoel24 API said: %s", data)
        raise ConfigEntryAuthFailed(data)
        

    def _update_mex(self):
        if self.session_id is None:
            self.login()
        with requests.post(BASE_URL + "/" + self.session_id + "/" + DATA_SERVICE_SUFFIX) as r:
            data = r.json()
           
            data = data["Items"]

        return data

    async def _async_update_data(self):
        # The data that is returned here can be accessed through coordinator.data.
        return await self.hass.async_add_executor_job(self._update_mex)


# End of file.
