"""Config flow for LLM Conversation Assist integration."""
from __future__ import annotations

import logging
import types
from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    TemplateSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)


from .const import *

from .langchain_tools.llm_models import (
    validate_tongyi_auth,
    validate_openai_auth,
    validate_qianfan_auth
)

_LOGGER = logging.getLogger(__name__)

STEP_MODEL_SELECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODEL_TYPE): SelectSelector(
            SelectSelectorConfig(
                options=[MODEL_TONGYI, MODEL_OPENAI, MODEL_QIANFAN],
                mode=SelectSelectorMode.DROPDOWN,
                multiple=False,
                translation_key="llm_model_class",
            )
        ),
    }
)

STEP_TONGYI_MODEL_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_TONGYI_CHAT_MODEL): str,
    }
)

STEP_OPENAI_MODEL_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_OPENAI_CHAT_MODEL): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_OPENAI_BASE_URL): str,
    }
)

STEP_QIANFAN_MODEL_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SECRET_KEY): str,
        vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_QIANFAN_CHAT_MODEL): str,
    }
)

STEP_COMMON_CONFIG_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
    }
)

DEFAULT_COMMON_OPTIONS = types.MappingProxyType(
    {
        CONF_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
        CONF_HUMAN_PROMPT: DEFAULT_HUMAN_PROMPT,
        CONF_LANGCHAIN_MAX_ITERATIONS: DEFAULT_LANGCHAIN_MAX_ITERATIONS,
        CONF_LANGCHAIN_MEMORY_WINDOW_SIZE: DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE
    }
)

DEFAULT_TONGYI_OPTIONS = types.MappingProxyType(
    {
        CONF_TOP_P: DEFAULT_TONGYI_TOP_P
    }
)

DEFAULT_OPENAI_OPTIONS = types.MappingProxyType(
    {
        CONF_TEMPERATURE: DEFAULT_OPENAI_TEMPERATURE,
        CONF_MAX_TOKENS: DEFAULT_OPENAI_MAX_TOKENS
    }
)

DEFAULT_QIANFAN_OPTIONS = types.MappingProxyType(
    {
        CONF_TOP_P: DEFAULT_QIANFAN_TOP_P,
        CONF_TEMPERATURE: DEFAULT_QIANFAN_TEMPERATURE
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LLM Conversation Assist."""

    VERSION = 1
    user_input_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        self.user_input_data = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_MODEL_SELECTION_SCHEMA,
            )

        if user_input[CONF_MODEL_TYPE] == MODEL_TONGYI:
            self.user_input_data[CONF_MODEL_TYPE] = MODEL_TONGYI
            return await self.async_step_tongyi()
        if user_input[CONF_MODEL_TYPE] == MODEL_OPENAI:
            self.user_input_data[CONF_MODEL_TYPE] = MODEL_OPENAI
            return await self.async_step_openai()
        if user_input[CONF_MODEL_TYPE] == MODEL_QIANFAN:
            self.user_input_data[CONF_MODEL_TYPE] = MODEL_QIANFAN
            return await self.async_step_qianfan()

        return self.async_show_form(
            step_id="user", data_schema=STEP_MODEL_SELECTION_SCHEMA, errors={CONF_MODEL_TYPE: "unknown"}
        )

    async def async_step_tongyi(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="tongyi", data_schema=STEP_TONGYI_MODEL_CONFIG_SCHEMA
            )

        errors = {}

        try:
            await self._validate_tongyi_conf(user_input)
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "auth fail"
        else:
            self.user_input_data[CONF_CHAT_MODEL] = user_input[CONF_CHAT_MODEL]
            self.user_input_data[CONF_API_KEY] = user_input[CONF_API_KEY]
            return await self.async_step_common_config()

        return self.async_show_form(step_id="tongyi", data_schema=STEP_TONGYI_MODEL_CONFIG_SCHEMA, errors=errors)

    async def async_step_openai(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="openai", data_schema=STEP_OPENAI_MODEL_CONFIG_SCHEMA
            )

        errors = {}

        try:
            await self._validate_openai_conf(user_input)
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "auth fail"
        else:
            self.user_input_data[CONF_CHAT_MODEL] = user_input[CONF_CHAT_MODEL]
            self.user_input_data[CONF_API_KEY] = user_input[CONF_API_KEY]
            self.user_input_data[CONF_BASE_URL] = user_input[CONF_BASE_URL]
            return await self.async_step_common_config()

        return self.async_show_form(step_id="openai", data_schema=STEP_OPENAI_MODEL_CONFIG_SCHEMA, errors=errors)

    async def async_step_qianfan(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="qianfan", data_schema=STEP_QIANFAN_MODEL_CONFIG_SCHEMA
            )

        errors = {}

        try:
            await self._validate_qianfan_auth(user_input)
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "auth fail"
        else:
            self.user_input_data[CONF_CHAT_MODEL] = user_input[CONF_CHAT_MODEL]
            self.user_input_data[CONF_API_KEY] = user_input[CONF_API_KEY]
            self.user_input_data[CONF_SECRET_KEY] = user_input[CONF_SECRET_KEY]
            return await self.async_step_common_config()

        return self.async_show_form(step_id="tongyi", data_schema=STEP_QIANFAN_MODEL_CONFIG_SCHEMA, errors=errors)

    async def async_step_common_config(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="common_config", data_schema=STEP_COMMON_CONFIG_DATA_SCHEMA
            )

        return self.async_create_entry(
            title=user_input.get(CONF_NAME, DEFAULT_NAME), data=self.user_input_data
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)

    async def _validate_tongyi_conf(self, data: dict[str, Any]):
        api_key = data[CONF_API_KEY]
        model_name = data[CONF_CHAT_MODEL]
        return await validate_tongyi_auth(api_key, model_name)

    async def _validate_openai_conf(self, data: dict[str, Any]):
        api_key = data[CONF_API_KEY]
        model_name = data[CONF_CHAT_MODEL]
        base_url = data[CONF_BASE_URL]
        return await validate_openai_auth(api_key, model_name, base_url)

    async def _validate_qianfan_auth(self, data: dict[str, Any]):
        ak = data[CONF_API_KEY]
        sk = data[CONF_SECRET_KEY]
        model_name = data[CONF_CHAT_MODEL]
        return await validate_qianfan_auth(ak, sk, model_name)


class OptionsFlow(config_entries.OptionsFlow):
    """LLM Conversation Assist config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input
            )
        schema = {}
        schema.update(self.common_config_option_schema(self.config_entry.options))
        schema.update(self.llm_config_option_schema(self.config_entry.options))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

    def common_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        if not options:
            options = DEFAULT_COMMON_OPTIONS

        return {
            vol.Optional(
                CONF_SYSTEM_PROMPT,
                description={"suggested_value": options[CONF_SYSTEM_PROMPT]},
                default=DEFAULT_SYSTEM_PROMPT,
            ): TemplateSelector(),
            vol.Optional(
                CONF_HUMAN_PROMPT,
                description={"suggested_value": options[CONF_HUMAN_PROMPT]},
                default=DEFAULT_HUMAN_PROMPT,
            ): TemplateSelector(),
            vol.Optional(
                CONF_LANGCHAIN_MAX_ITERATIONS,
                description={"suggested_value": options[CONF_LANGCHAIN_MAX_ITERATIONS]},
                default=DEFAULT_LANGCHAIN_MAX_ITERATIONS,
            ): int,
            vol.Optional(
                CONF_LANGCHAIN_MEMORY_WINDOW_SIZE,
                description={"suggested_value": options[CONF_LANGCHAIN_MEMORY_WINDOW_SIZE]},
                default=DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE,
            ): int,
        }

    def llm_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        if self.config_entry.data.get(CONF_MODEL_TYPE) == MODEL_TONGYI:
            return self.tongyi_config_option_schema(options)
        if self.config_entry.data.get(CONF_MODEL_TYPE) == MODEL_OPENAI:
            return self.openai_config_option_schema(options)
        if self.config_entry.data.get(CONF_MODEL_TYPE) == MODEL_QIANFAN:
            return self.qianfan_config_option_schema(options)
        return {}

    def tongyi_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        if not options:
            options = DEFAULT_TONGYI_OPTIONS

        return {
            vol.Optional(
                CONF_TOP_P,
                description={"suggested_value": options[CONF_TOP_P]},
                default=DEFAULT_TONGYI_TOP_P,
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
        }

    def openai_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        if not options:
            options = DEFAULT_OPENAI_OPTIONS

        return {
            vol.Optional(
                CONF_TEMPERATURE,
                description={"suggested_value": options[CONF_TEMPERATURE]},
                default=DEFAULT_OPENAI_TEMPERATURE,
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
            vol.Optional(
                CONF_MAX_TOKENS,
                description={"suggested_value": options[CONF_MAX_TOKENS]},
                default=DEFAULT_OPENAI_MAX_TOKENS,
            ): int,
        }

    def qianfan_config_option_schema(self, options: MappingProxyType[str, Any]) -> dict:
        if not options:
            options = DEFAULT_QIANFAN_OPTIONS

        if self.config_entry.data.get(CONF_CHAT_MODEL) not in ("ERNIE-Bot", "ERNIE-Bot-turbo"):
            return {}

        return {
            vol.Optional(
                CONF_TOP_P,
                description={"suggested_value": options[CONF_TOP_P]},
                default=DEFAULT_QIANFAN_TOP_P,
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
            vol.Optional(
                CONF_TEMPERATURE,
                description={"suggested_value": options[CONF_TEMPERATURE]},
                default=DEFAULT_QIANFAN_TEMPERATURE,
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
        }
