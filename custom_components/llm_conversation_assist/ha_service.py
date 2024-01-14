import asyncio
import csv
import io
import os
import uuid
import voluptuous as vol
from typing import Any

from homeassistant.core import Service
from homeassistant.core import HomeAssistant
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.components import conversation
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, CONF_ID, SERVICE_RELOAD
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml

from homeassistant.components.automation.config import (
    async_validate_config_item as async_validate_automation_config_item,
    DOMAIN as AUTOMATION_DOMAIN
)

from homeassistant.config import (
    AUTOMATION_CONFIG_PATH,
    SCRIPT_CONFIG_PATH,
    SCENE_CONFIG_PATH
)

from homeassistant.components.script.config import (
    async_validate_config_item as async_validate_script_config_item
)

from homeassistant.components.scene import (
    DOMAIN as SCENE_DOMAIN,
    PLATFORM_SCHEMA as SCENE_CONFIG_SCHEMA
)

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

import logging

_LOGGER = logging.getLogger(__name__)


def _read(path):
    """Read YAML helper."""
    if not os.path.isfile(path):
        return None

    return load_yaml(path)


def _write(path, data):
    """Write YAML helper."""
    # Do it before opening file. If dump causes error it will now not
    # truncate the file.
    contents = dump(data)
    write_utf8_file_atomic(path, contents)


class HaService:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.mutation_lock = asyncio.Lock()

    async def get_all_exposed_entities(self):
        states = [
            state
            for state in self.hass.states.async_all()
            if async_should_expose(self.hass, conversation.DOMAIN, state.entity_id)
        ]
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)
        exposed_entities = []
        for state in states:
            entity_id = state.entity_id
            entity = ent_reg.async_get(entity_id)
            aliases = []
            if entity and entity.aliases:
                aliases = entity.aliases
            if entity and entity.device_id:
                device_entry = dev_reg.devices.get(entity.device_id)
            else:
                device_entry = None

            if entity and entity.area_id:
                area_id = entity.area_id
            elif device_entry and device_entry.area_id:
                area_id = device_entry.area_id
            else:
                area_id = None

            if area_id is not None:
                area_entry = area_reg.async_get_area(area_id)
            else:
                area_entry = None

            area_name = "UNKNOWN"
            if area_entry is not None:
                area_name = area_entry.name

            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                    "area_id": area_id,
                    "area_name": area_name,
                }
            )
        return exposed_entities

    async def get_all_exposed_entities_csv(self):
        exposed_entities = await self.get_all_exposed_entities()
        if len(exposed_entities) == 0:
            return ""

        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        field_names = list(exposed_entities[0].keys())
        writer.writerow(field_names)

        for row in exposed_entities:
            writer.writerow(row.values())

        return csv_data.getvalue()

    async def should_expose(self, entity_id: str) -> bool:
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        return async_should_expose(self.hass, conversation.DOMAIN, entity_id)

    async def add_automation(self, new_automation):
        _LOGGER.info(new_automation)
        try:
            await async_validate_automation_config_item(self.hass, "", new_automation)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return False

        async with self.mutation_lock:
            # load & update
            current_automation = await self.read_current_automation()
            self._write_automation_value(current_automation, uuid.uuid4().hex, new_automation)

            await self.hass.async_add_executor_job(_write, self.hass.config.path(AUTOMATION_CONFIG_PATH),
                                                   current_automation)

        await self.hass.services.async_call(AUTOMATION_DOMAIN, SERVICE_RELOAD)
        return True

    async def read_current_automation(self):
        """Read the config."""
        current = await self.hass.async_add_executor_job(_read, self.hass.config.path(AUTOMATION_CONFIG_PATH))
        if not current:
            current = []
        return current

    def _write_automation_value(self, current_automation, config_key, new_value):
        """Set value."""
        _LOGGER.info("current automation: %s", current_automation)
        _LOGGER.info("new value: %s", new_value)
        _LOGGER.info("config_key: %s", config_key)
        updated_value = {CONF_ID: config_key}

        # Iterate through some keys that we want to have ordered in the output
        for key in ("alias", "description", "trigger", "condition", "action"):
            if key in new_value:
                updated_value[key] = new_value[key]

        # We cover all current fields above, but just in case we start
        # supporting more fields in the future.
        updated_value.update(new_value)

        updated = False
        for index, cur_value in enumerate(current_automation):
            # When people copy paste their automations to the config file,
            # they sometimes forget to add IDs. Fix it here.
            if CONF_ID not in cur_value:
                cur_value[CONF_ID] = uuid.uuid4().hex

            elif cur_value[CONF_ID] == config_key:
                current_automation[index] = updated_value
                updated = True

        if not updated:
            current_automation.append(updated_value)

        _LOGGER.info("current automation: %s", current_automation)

    async def call_service(
            self,
            domain: str,
            service: str,
            entity_id: str,
            service_data: dict[str, Any] | None = None,
    ):
        if not self.hass.services.has_service(domain, service):
            return False
        if service_data is None:
            service_data = {}

        ent_reg = er.async_get(self.hass)
        entity = ent_reg.async_get(entity_id)
        if entity is None:
            return f"Unknown entity {entity_id}"
        if not await self.should_expose(entity_id):
            return f"Unexposed entity {entity_id}"

        service_data["entity_id"] = entity_id
        try:
            await self.hass.services.async_call(
                domain=domain,
                service=service,
                service_data=service_data,
            )
            return True
        except HomeAssistantError:
            return False

    async def get_available_services(self, domain: str) -> dict[str, Service]:
        all_services = self.hass.services.async_services()
        return all_services.get(domain.lower(), {})

    async def add_script(self, script_id, new_script):
        _LOGGER.info(new_script)
        try:
            await async_validate_script_config_item(self.hass, script_id, new_script)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return False

        async with self.mutation_lock:
            # load & update
            current_script = await self.read_current_script()
            current_script[script_id] = new_script

            await self.hass.async_add_executor_job(_write, self.hass.config.path(SCRIPT_CONFIG_PATH),
                                                   current_script)

        await self.hass.services.async_call(SCRIPT_DOMAIN, SERVICE_RELOAD)
        return True

    async def read_current_script(self):
        """Read the config."""
        current = await self.hass.async_add_executor_job(_read, self.hass.config.path(SCRIPT_CONFIG_PATH))
        if not current:
            current = {}
        return current

    async def add_scene(self, new_scene):
        _LOGGER.info(new_scene)
        try:
            SCENE_CONFIG_SCHEMA(new_scene)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return False

        async with self.mutation_lock:
            # load & update
            current_scenes = await self._read_current_scenes()
            self._write_scene_value(current_scenes, uuid.uuid4().hex, new_scene)

            await self.hass.async_add_executor_job(_write, self.hass.config.path(SCENE_CONFIG_PATH),
                                                   current_scenes)

        await self.hass.services.async_call(SCENE_DOMAIN, SERVICE_RELOAD)
        return True

    async def _read_current_scenes(self):
        """Read the config."""
        current = await self.hass.async_add_executor_job(_read, self.hass.config.path(SCENE_CONFIG_PATH))
        if not current:
            current = []
        return current

    def _write_scene_value(self, current_scenes, config_key, new_value):
        """Set value."""
        updated_value = {CONF_ID: config_key}
        # Iterate through some keys that we want to have ordered in the output
        for key in ("name", "entities"):
            if key in new_value:
                updated_value[key] = new_value[key]

        # We cover all current fields above, but just in case we start
        # supporting more fields in the future.
        updated_value.update(new_value)

        updated = False
        for index, cur_value in enumerate(current_scenes):
            # When people copy paste their scenes to the config file,
            # they sometimes forget to add IDs. Fix it here.
            if CONF_ID not in cur_value:
                cur_value[CONF_ID] = uuid.uuid4().hex

            elif cur_value[CONF_ID] == config_key:
                current_scenes[index] = updated_value
                updated = True

        if not updated:
            current_scenes.append(updated_value)

