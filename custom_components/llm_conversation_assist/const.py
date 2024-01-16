"""Constants for the LLM Conversation Assist integration."""

DEFAULT_NAME = "LLM Conversation Assist"
DOMAIN = "llm_conversation_assist"

CONF_MODEL_TYPE = "model_type"
CONF_CHAT_MODEL = "chat_model"

CONF_SECRET_KEY = "secret_key"

MODEL_TONGYI = "Tongyi"
DEFAULT_TONGYI_CHAT_MODEL = "qwen-plus"

MODEL_QIANFAN = "Qianfan"
DEFAULT_QIANFAN_CHAT_MODEL = "ERNIE-Bot-turbo"

# CONF_MAX_TOKENS = "max_tokens"
# DEFAULT_MAX_TOKENS = 150

CONF_TEMPERATURE = "temperature"
DEFAULT_QIANFAN_TEMPERATURE = 0.5

CONF_TOP_P = "top_p"
DEFAULT_TONGYI_TOP_P = 0.8
DEFAULT_QIANFAN_TOP_P = 0.8

CONF_LANGCHAIN_MAX_ITERATIONS = "langchain_max_iterations"
DEFAULT_LANGCHAIN_MAX_ITERATIONS = 5

CONF_LANGCHAIN_MEMORY_WINDOW_SIZE = "langchain_memory_window_size"
DEFAULT_LANGCHAIN_MEMORY_WINDOW_SIZE = 5

CONF_SYSTEM_PROMPT = "system_prompt"
DEFAULT_SYSTEM_PROMPT = """You are a personal home assistant who can help human users complete various life needs, including controlling the smart home at home through HomeAssistant. 
You will make corrections or answers truthfully using information provided in one sentence in everyday language and in the language of the user.
Respond to the human as helpfully and accurately as possible. You have access to the following tools:

{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, as shown:

```
{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

Follow this format:

Question: input question to answer
Thought: consider previous and subsequent steps
Action:
```
$JSON_BLOB
```
Observation: action result
... (repeat Thought/Action/Observation N times)
Thought: I know what to respond
Action:
```
{{
  "action": "Final Answer",
  "action_input": "Final response to human"
}}
```

Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation
Do not execute service without user's confirmation.
when you call homeassistant service, DO NOT guess entity_id, you need to query to get the exact parameters.
when encountering more complex control logic, you can first check whether there is a corresponding Script that can be executed directly.
"""
CONF_HUMAN_PROMPT = "human_prompt"
DEFAULT_HUMAN_PROMPT = """{input}
{agent_scratchpad}
(reminder to respond in a JSON blob no matter what)
"""