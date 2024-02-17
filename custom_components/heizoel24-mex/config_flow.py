"""Config flow for EcoFrog integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, BASE_URL, LOGIN_SERVICE

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str
    }
)


def test_auth(username: str, password: str) -> bool:
    """Test if we can authenticate with the host."""

    REQ = { "Username" : username ,
           "Password" : password}
    _LOGGER.error(REQ)
    with requests.post(BASE_URL + LOGIN_SERVICE, json=REQ) as r:
        _LOGGER.error("Authenticating: %s", r.text)
        try:
            data = r.json()
        except json.JSONDecodeError as e:
                if "login" in data.casefold():
                    raise ConfigEntryAuthFailed(data) from e
                _LOGGER.error("E-sensorix API said: %s", data)
                return False
        if r.status_code == 200:
            _LOGGER.debug(r.text)
            if data['ResultCode'] == 0:
                session_id = data['SessionId']
                _LOGGER.info('Session ID: ' + session_id)
                return True
        return False



class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoFrog."""

    VERSION = 1

    async def validate_input(
        self, hass: HomeAssistant, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
        """
        # If your PyPI package is not built with async, pass your methods
        # to the executor:
        # await hass.async_add_executor_job(
        #     your_validate_func, data["username"], data["password"]
        # )

        args = data["username"], data["password"]
        auth_data = await hass.async_add_executor_job(test_auth, *args)
        if not data:
            raise InvalidAuth

        # If you cannot connect:
        # throw CannotConnect
        # If the authentication is wrong:
        # InvalidAuth

        # Return info that you want to store in the config entry.
        return auth_data

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        title = "Mex " + user_input["username"]

        try:
            info = await self.validate_input(self.hass, user_input)
         
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception %s", str(e))
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
