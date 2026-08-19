"""Config flow for Ecovacs Map Data."""

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN


class EcovacsMapDataConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Ecovacs Map Data."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the single companion integration entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Ecovacs Map Data", data={})
        return self.async_show_form(step_id="user")

