"""The LLM Conversation Assist integration."""
from __future__ import annotations

import logging
from typing import Literal

from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import (
    AgentExecutor,
    create_structured_chat_agent,
    create_openai_tools_agent
)
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent, template
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
)

from .const import *

from .langchain_tools.ha_tools import (
    HAServiceCallToolkit
)

from .ha_service import HaService

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LLM Conversation Assist from a config entry."""

    try:
        await validate_config(hass, entry)
    except Exception as err:
        raise ConfigEntryNotReady(err) from err

    agent = LLMConversationAssistAgent(hass, entry)

    conversation.async_set_agent(hass, entry, agent)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload LLM Conversation Assist."""
    conversation.async_unset_agent(hass, entry)
    return True


async def validate_config(hass: HomeAssistant, entry: ConfigEntry):
    pass


class LLMConversationAssistAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.memory = ConversationBufferWindowMemory(
            return_messages=True,
            memory_key='chat_history',
            input_key='input',
            k=self.entry.options.get(CONF_LANGCHAIN_MEMORY_WINDOW_SIZE, DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE)
        )
        self.tools = HAServiceCallToolkit(HaService(self.hass)).get_tools()

    def _get_agent_chain(self):
        llm = self._get_llm()
        if llm is None:
            raise ConfigEntryNotReady

        raw_system_prompt = self.entry.options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        raw_human_prompt = self.entry.options.get(CONF_HUMAN_PROMPT, DEFAULT_HUMAN_PROMPT)
        if self.entry.data.get(CONF_MODEL_TYPE) == MODEL_OPENAI:
            system_prompt = self._async_generate_system_prompt(raw_system_prompt, OPENAI_AGENT_SYSTEM_PROMPT)
            human_prompt = self._async_generate_human_prompt(raw_human_prompt, OPENAI_AGENT_HUMAN_PROMPT)
            _LOGGER.debug("Using system prompt: %s", system_prompt)
            _LOGGER.debug("Using human prompt: %s", human_prompt)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder('chat_history'),
                ("human", human_prompt),
                MessagesPlaceholder('agent_scratchpad'),
            ])
            agent = create_openai_tools_agent(
                llm=llm,
                tools=self.tools,
                prompt=prompt
            )
        else:
            system_prompt = self._async_generate_system_prompt(raw_system_prompt, STRUCTURED_AGENT_SYSTEM_PROMPT)
            human_prompt = self._async_generate_human_prompt(raw_human_prompt, STRUCTURED_AGENT_HUMAN_PROMPT)
            _LOGGER.debug("Using system prompt: %s", system_prompt)
            _LOGGER.debug("Using human prompt: %s", human_prompt)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder('chat_history'),
                ("human", human_prompt)
            ])
            agent = create_structured_chat_agent(
                llm=llm,
                tools=self.tools,
                prompt=prompt
            )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=self.entry.options.get(CONF_LANGCHAIN_MAX_ITERATIONS, DEFAULT_LANGCHAIN_MAX_ITERATIONS),
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True
        )

    def _get_llm(self):
        model_type = self.entry.data.get(CONF_MODEL_TYPE)
        if model_type == MODEL_TONGYI:
            return self._get_tongyi_model()
        if model_type == MODEL_OPENAI:
            return self._get_openai_model()
        if model_type == MODEL_QIANFAN:
            return self._get_qianfan_model()

    def _get_tongyi_model(self):
        from langchain_community.llms import Tongyi
        api_key = self.entry.data.get(CONF_API_KEY)
        model_name = self.entry.data.get(CONF_CHAT_MODEL, DEFAULT_TONGYI_CHAT_MODEL)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TONGYI_TOP_P)
        return Tongyi(model_name=model_name, dashscope_api_key=api_key, top_p=top_p)

    def _get_openai_model(self):
        from langchain_openai import ChatOpenAI
        api_key = self.entry.data.get(CONF_API_KEY)
        model_name = self.entry.data.get(CONF_CHAT_MODEL, DEFAULT_OPENAI_CHAT_MODEL)
        base_url = self.entry.data.get(CONF_BASE_URL, DEFAULT_OPENAI_BASE_URL)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_OPENAI_TEMPERATURE)
        max_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_OPENAI_MAX_TOKENS)
        return ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def _get_qianfan_model(self):
        from langchain_community.chat_models import QianfanChatEndpoint
        ak = self.entry.data.get(CONF_API_KEY)
        sk = self.entry.data.get(CONF_SECRET_KEY)
        model_name = self.entry.data.get(CONF_CHAT_MODEL, DEFAULT_QIANFAN_CHAT_MODEL)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_QIANFAN_TOP_P)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_QIANFAN_TEMPERATURE)
        return QianfanChatEndpoint(qianfan_ak=ak, qianfan_sk=sk, model=model_name, top_p=top_p, temperature=temperature)

    def _async_generate_system_prompt(self, raw_prompt: str, agent_prompt: str) -> str:
        """Generate a prompt for the user."""
        service = HaService(self.hass)
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
                "exposed_areas": service.get_all_exposed_areas(),
                "exposed_entities": service.get_all_exposed_entities(),
                "agent_system_prompt": agent_prompt
            },
            parse_result=False,
        )

    def _async_generate_human_prompt(self, raw_prompt: str, agent_prompt: str) -> str:
        """Generate a prompt for the user."""
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "agent_human_prompt": agent_prompt
            },
            parse_result=False,
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_process(
            self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        agent_chain = self._get_agent_chain()

        user_message = {"role": "user", "input": user_input.text}
        try:
            response = await agent_chain.ainvoke(user_message)
        except HomeAssistantError as err:
            _LOGGER.error(err, exc_info=err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Something went wrong: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=user_input.conversation_id
            )
        except Exception as err:
            _LOGGER.error(err, exc_info=err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Something went wrong: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=user_input.conversation_id
            )

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response["output"])
        return conversation.ConversationResult(
            response=intent_response, conversation_id=user_input.conversation_id
        )

