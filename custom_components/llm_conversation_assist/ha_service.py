import asyncio
import csv
import io
import os
import uuid
import voluptuous as vol
from typing import Any

from homeassistant.core import callback
from homeassistant.core import Service
from homeassistant.core import HomeAssistant
from homeassistant.components.conversation import DOMAIN as CONVERSATION_DOMAIN
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.script.config import async_validate_config_item as async_validate_script_config_item
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml

from homeassistant.components.automation.config import (
    async_validate_config_item as async_validate_automation_config_item,
    DOMAIN as AUTOMATION_DOMAIN
)

from homeassistant.const import (
    CLOUD_NEVER_EXPOSED_ENTITIES,
    CONF_ID,
    SERVICE_RELOAD
)
from homeassistant.config import (
    AUTOMATION_CONFIG_PATH,
    SCRIPT_CONFIG_PATH,
    SCENE_CONFIG_PATH
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

    @callback
    def _get_registry_entries(
            self, entity_id: str
    ) -> tuple[er.RegistryEntry | None, dr.DeviceEntry | None, ar.AreaEntry | None,]:
        """Get registry entries."""
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)
        area_reg = ar.async_get(self.hass)

        if (entity_entry := ent_reg.async_get(entity_id)) and entity_entry.device_id:
            device_entry = dev_reg.devices.get(entity_entry.device_id)
        else:
            device_entry = None

        if entity_entry and entity_entry.area_id:
            area_id = entity_entry.area_id
        elif device_entry and device_entry.area_id:
            area_id = device_entry.area_id
        else:
            area_id = None

        if area_id is not None:
            area_entry = area_reg.async_get_area(area_id)
        else:
            area_entry = None

        return entity_entry, device_entry, area_entry

    async def _read_current_automation(self):
        """Read the config."""
        current = await self.hass.async_add_executor_job(_read, self.hass.config.path(AUTOMATION_CONFIG_PATH))
        if not current:
            current = []
        return current

    def _write_automation_value(self, current_automation, config_key, new_value):
        """Set value."""
        _LOGGER.debug("current automation: %s", current_automation)
        _LOGGER.debug("new value: %s", new_value)
        _LOGGER.debug("config_key: %s", config_key)
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

    def _is_valid_entity_id(self, entity_id):
        ent_reg = er.async_get(self.hass)
        entity = ent_reg.async_get(entity_id)
        return entity is not None

    def _is_valid_area_id(self, area_id):
        area_reg = ar.async_get(self.hass)
        area = area_reg.async_get_area(area_id)
        return area is not None

    def _is_valid_device_id(self, entity_id):
        dev_reg = dr.async_get(self.hass)
        device = dev_reg.devices.get(entity_id)
        return device is not None

    @callback
    def get_all_exposed_entities(self):
        _LOGGER.debug("Getting all exposed entities")
        states = [
            state
            for state in self.hass.states.async_all()
            if self.should_expose(state.entity_id)
        ]

        exposed_entities = []
        for state in states:
            entity_id = state.entity_id
            domain = state.domain
            entity_entry, device_entry, area_entry = self._get_registry_entries(entity_id)

            aliases = []
            if entity_entry and entity_entry.aliases:
                aliases = entity_entry.aliases

            area_id = ""
            area_name = "UNKNOWN"
            area_aliases = []
            if area_entry:
                area_id = area_entry.id
                area_name = area_entry.name
                area_aliases = area_entry.aliases

            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "domain": domain,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                    "area_id": area_id,
                    "area_name": area_name,
                    "area_aliases": area_aliases
                }
            )
        return exposed_entities

    @callback
    def get_all_exposed_areas(self):
        exposed_entities = self.get_all_exposed_entities()
        if len(exposed_entities) == 0:
            return ""

        area_id_set = set()
        areas = []
        for exposed_entity in exposed_entities:
            area_id = exposed_entity.get("area_id", "")
            area_name = exposed_entity.get("area_name", "")
            area_aliases = exposed_entity.get("area_aliases", [])
            if (not isinstance(area_id, str) or area_id == "" or not isinstance(area_name, str) or area_name == "" or
                    area_id in area_id_set):
                continue
            area_id_set.add(area_id)
            areas.append({
                "area_id": area_id,
                "name": area_name,
                "aliases": area_aliases
            })

        return areas

    @callback
    def get_exposed_entities_csv(self, area_id: str | None = None, domain: str | None = None):
        _LOGGER.debug("Getting all exposed entities csv, area_id: %s, domain: %s", area_id, domain)
        all_exposed_entities = self.get_all_exposed_entities()

        need_fields = ["entity_id", "name", "aliases", "state"]
        filter_funcs = []
        if area_id is not None and area_id != "":
            filter_funcs.append(lambda entity: entity["area_id"] == area_id)
        else:
            need_fields.append("area_name")

        if domain is not None and domain != "":
            filter_funcs.append(lambda entity: entity["domain"] == domain)
        else:
            need_fields.append("domain")

        exposed_entities = []
        for exposed_entity in all_exposed_entities:
            is_exclude = False
            for filter_func in filter_funcs:
                if not filter_func(exposed_entity):
                    is_exclude = True
                    break
            if is_exclude:
                continue
            exposed_entities.append(exposed_entity)
        if len(exposed_entities) == 0:
            return "No exposed entities"

        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(need_fields)

        for exposed_entity in exposed_entities:
            row = []
            for field in need_fields:
                row.append(exposed_entity[field])
            writer.writerow(row)

        return f"""```csv
        {csv_data.getvalue()}
        ```
        """

    @callback
    def should_expose(self, entity_id: str) -> bool:
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        return async_should_expose(self.hass, CONVERSATION_DOMAIN, entity_id)

    async def add_automation(self, new_automation=None):
        _LOGGER.debug("Adding automation: %s", new_automation)
        if new_automation is None:
            return "You need to pass in new automation as a param named new_automation"
        try:
            await async_validate_automation_config_item(self.hass, "", new_automation)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return f"new_automation malformed: {err}"

        async with self.mutation_lock:
            # load & update
            current_automation = await self._read_current_automation()
            self._write_automation_value(current_automation, uuid.uuid4().hex, new_automation)

            await self.hass.async_add_executor_job(_write, self.hass.config.path(AUTOMATION_CONFIG_PATH),
                                                   current_automation)

        await self.hass.services.async_call(AUTOMATION_DOMAIN, SERVICE_RELOAD)
        return True

    async def call_service(
            self,
            domain: str,
            service: str,
            service_data: dict[str, Any] | None = None,
    ):
        _LOGGER.debug("Calling service: %s %s %s", domain, service, service_data)
        if not self.hass.services.has_service(domain, service):
            return f"Unknown service"

        valid_service_data = False
        if service_data is None:
            service_data = {}

        if "entity_id" in service_data:
            entity_id = service_data["entity_id"]
            if not isinstance(entity_id, list):
                entity_id = [entity_id]
            for e_id in entity_id:
                if not self._is_valid_entity_id(e_id):
                    return f"Unknown entity_id: {e_id}, you should reacquire exposed entities, entity_id should be of string type and the format should conform to domain.unique_id, like lgiht.123"
                if not self.should_expose(e_id):
                    return f"Unexposed entity {e_id}"
            valid_service_data = True

        if "area_id" in service_data:
            valid_service_data = True
            area_id = service_data["area_id"]
            if not self._is_valid_area_id(area_id):
                return f"Unknown area_id: {area_id}, you should reacquire exposed entities"

        if "device_id" in service_data:
            valid_service_data = True
            device_id = service_data["device_id"]
            if not self._is_valid_device_id(device_id):
                return f"Unknown device_id: {device_id}, you should reacquire exposed entities"

        if not valid_service_data:
            return f"Invalid service data: {service_data}, must contain at least one of the following: area_id, device_id, entity_id."

        try:
            await self.hass.services.async_call(
                domain=domain,
                service=service,
                service_data=service_data,
            )
            return True
        except HomeAssistantError as e:
            return str(e)
        except Exception as e:
            return str(e)

    async def get_available_services(self, domain: str) -> dict[str, Service]:
        _LOGGER.debug("Getting available services for %s", domain)
        all_services = self.hass.services.async_services()
        return all_services.get(domain.lower(), {})

    async def add_script(self, script_id, new_script=None):
        _LOGGER.debug("Adding script: %s", new_script)
        if new_script is None:
            return "You need to pass in new script as a param named new_script"
        try:
            await async_validate_script_config_item(self.hass, script_id, new_script)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return f"new_script malformed: {err}"

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

    async def add_scene(self, name: str = "", entities: dict[str, Any] = None):
        _LOGGER.debug("Adding scene, name: %s, entities: %s", name, entities)
        if name is None or name == "":
            return "You need to specify a name of the new scene"
        if entities is None or len(entities) == 0:
            return "You need to specify at least one entity in the new scene"

        for entity_id in entities.keys():
            if not self._is_valid_entity_id(entity_id):
                return f"Unknown entity_id: {entity_id}, the key of entities should be entity_id, of string type and the format should conform to domain.unique_id, like lgiht.123"
            if not self.should_expose(entity_id):
                return f"Unexposed entity {entity_id}"

        new_scene = {
            "name": name,
            "entities": entities
        }
        try:
            SCENE_CONFIG_SCHEMA(new_scene)
        except (vol.Invalid, HomeAssistantError) as err:
            _LOGGER.error(err)
            return f"new_scene malformed: {err}"

        entities = new_scene.get("entities", [])
        for entity_id in entities:
            if not self._is_valid_entity_id(entity_id):
                return f"Unknown entity_id: {entity_id}, you should reacquire exposed entities"
            if not self.should_expose(entity_id):
                return f"Unexposed entity {entity_id}"

        async with self.mutation_lock:
            # load & update
            current_scenes = await self._read_current_scenes()
            self._write_scene_value(current_scenes, uuid.uuid4().hex, new_scene)

            await self.hass.async_add_executor_job(_write, self.hass.config.path(SCENE_CONFIG_PATH),
                                                   current_scenes)

        await self.hass.services.async_call(SCENE_DOMAIN, SERVICE_RELOAD)
        return True

