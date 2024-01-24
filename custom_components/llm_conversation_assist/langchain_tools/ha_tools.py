from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import StructuredTool
from ..ha_service import HaService
from typing import Any


class HAServiceCallInput(BaseModel):
    domain: str = Field(description="domain in Home Assistant")
    service: str = Field(description="service in Home Assistant")
    service_data: dict = Field(
        description="service_data is a map that contains at least one of the following: area_id, device_id, entity_id. Each of these can be a list. Additional parameters can also be passed in, such as brightness when operating a light.",
        default={}
    )


class HAGetAvailableServicesInput(BaseModel):
    domain: str = Field(description="domain in Home Assistant")


class HAGetExposedEntitiesInput(BaseModel):
    area_id: str = Field(description="optional, area_id in Home Assistant, corresponding to the area where the entities you want to query is located", default=None)
    domain: str = Field(description="optional, domain in Home Assistant, corresponding to the entities you want to query", default=None)


class HAAddAutomationInput(BaseModel):
    new_automation: dict[str, Any] = Field(description="the automation to be added, should be valid Home Assistant config item", default=None)


class HAAddScriptInput(BaseModel):
    script_id: str = Field(description="the unique id of script in homeassistant, needs to represent the meaning of the script as much as possible, and can only contain letters, numbers and underscore(_) characters.")
    new_script: dict[str, Any] = Field(description="the script to be added, should be valid homeassistant config item", default=None)


class HAAddSceneInput(BaseModel):
    name: str = Field(description="required, the name of new scene", default="")
    entities: dict[str, Any] = Field(description="required, entities to control and their desired state, key is entity_id.", default=None)


class HAServiceCallToolkit(object):
    def __init__(self, ha_service: HaService):
        self.ha_service = ha_service
        self.tools = []
        self.build_tools()

    def get_tools(self):
        return self.tools

    def build_tools(self):
        self.tools = [
            self.build_get_exposed_entities_tool(),
            self.build_get_available_services_tool(),
            self.build_service_call_tool(),
            self.build_add_automation_tool(),
            self.build_add_script_tool(),
            self.build_add_scene_tool()
        ]

    def build_service_call_tool(self):
        service_tool = StructuredTool.from_function(
            coroutine=self.ha_service.call_service,
            name="call_homeassistant_service",
            description="use this tool to call homeassistant services, including scene/automation/script, you may have to figure out exposed entities before you use this tool",
            args_schema=HAServiceCallInput,
            return_direct=False,
            handle_tool_error=True,
        )
        return service_tool

    def build_get_available_services_tool(self):
        available_services_tool = StructuredTool.from_function(
            coroutine=self.ha_service.get_available_services,
            name="get_domains_services",
            description="use this tool to get all available services of the given domain, when you're not sure what services a domain has or which service should be used",
            args_schema=HAGetAvailableServicesInput,
            return_direct=False
        )
        return available_services_tool

    def build_get_exposed_entities_tool(self):
        exposed_entities_tool = StructuredTool.from_function(
            func=self.ha_service.get_exposed_entities_csv,
            name="get_all_exposed_entities",
            description="use this tool to get all exposed entities, this tool should be called before you want to call a service of an entity, the data is csv format",
            args_schema=HAGetExposedEntitiesInput,
            return_direct=False
        )
        return exposed_entities_tool

    def build_add_automation_tool(self):
        automation_tool = StructuredTool.from_function(
            coroutine=self.ha_service.add_automation,
            name="add_homeassistant_automation",
            description="use this tool to add an automation in Home Assistant, you need to get the exact value of entity_id/area_id/device_id instead of guessing",
            args_schema=HAAddAutomationInput,
            return_direct=False,
            handle_tool_error=True,
        )
        return automation_tool

    def build_add_script_tool(self):
        add_script_tool = StructuredTool.from_function(
            coroutine=self.ha_service.add_script,
            name="add_homeassistant_script",
            description="use this tool to add an script in Home Assistant, you need to get the exact value of entity_id/area_id/device_id instead of guessing",
            args_schema=HAAddScriptInput,
            return_direct=False,
            handle_tool_error=True,
        )
        return add_script_tool

    def build_add_scene_tool(self):
        add_script_tool = StructuredTool.from_function(
            coroutine=self.ha_service.add_scene,
            name="add_homeassistant_scene",
            description="use this tool to add a scene in Home Assistant, you need to get the exact value of entity_id/area_id/device_id instead of guessing",
            args_schema=HAAddSceneInput,
            return_direct=False,
            handle_tool_error=True,
        )
        return add_script_tool

