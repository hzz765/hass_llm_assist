"""The LLM Conversation Assist integration."""
from __future__ import annotations

import logging
from typing import Literal

from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import (
    AgentExecutor,
    create_structured_chat_agent
)
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
)

from .const import (
    CONF_MODEL_TYPE,
    MODEL_TONGYI,
    DEFAULT_TONGYI_CHAT_MODEL,
    CONF_CHAT_MODEL,
    CONF_SYSTEM_PROMPT,
    CONF_HUMAN_PROMPT,
    CONF_TOP_P,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_HUMAN_PROMPT,
    DEFAULT_TONGYI_TOP_P,
    DOMAIN,
    CONF_LANGCHAIN_MAX_ITERATIONS,
    DEFAULT_LANGCHAIN_MAX_ITERATIONS,
    CONF_LANGCHAIN_MEMORY_WINDOW_SIZE,
    DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE
)

from .langchain_tools.ha_tools import (
    HAServiceCallToolFactory
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
    hass.data[DOMAIN].pop(entry.entry_id)
    conversation.async_unset_agent(hass, entry)
    return True


async def validate_config(hass: HomeAssistant, entry: ConfigEntry):
    pass


class LLMConversationAssistAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.agent_chain = self._get_agent_chain()

    def _get_agent_chain(self):
        llm = self._get_llm()
        if llm is None:
            raise ConfigEntryNotReady

        tools = HAServiceCallToolFactory(HaService(self.hass)).get_tools()

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.entry.options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)),
            MessagesPlaceholder('chat_history'),
            ("human", self.entry.options.get(CONF_HUMAN_PROMPT, DEFAULT_HUMAN_PROMPT))
        ])
        memory = ConversationBufferWindowMemory(
            return_messages=True,
            memory_key='chat_history',
            input_key='input',
            k=self.entry.options.get(CONF_LANGCHAIN_MEMORY_WINDOW_SIZE, DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE)
        )

        agent = create_structured_chat_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        return AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self.entry.options.get(CONF_LANGCHAIN_MAX_ITERATIONS, DEFAULT_LANGCHAIN_MAX_ITERATIONS),
            verbose=True,
            memory=memory,
            handle_parsing_errors=True
        )

    def _get_llm(self):
        model_type = self.entry.data.get(CONF_MODEL_TYPE)
        if model_type == MODEL_TONGYI:
            return self._get_tongyi_model()

    def _get_tongyi_model(self):
        from langchain_community.llms import Tongyi
        api_key = self.entry.data.get(CONF_API_KEY)
        model_name = self.entry.data.get(CONF_CHAT_MODEL, DEFAULT_TONGYI_CHAT_MODEL)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TONGYI_TOP_P)
        return Tongyi(model_name=model_name, dashscope_api_key=api_key, top_p=top_p)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_process(
            self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:

        user_message = {"role": "user", "input": user_input.text}
        try:
            response = await self.agent_chain.ainvoke(user_message)
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

