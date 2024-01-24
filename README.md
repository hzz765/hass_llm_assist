# LLM Assist For Homeassistant
>MVP (minimum viable product) version, there are still many things that can be optimized and will be gradually improved.
>
>If you have any ideas or suggestions, you can raise an issue to tell me.

English | [简体中文](README_zh.md)

This component integrates the power of [LangChain](https://github.com/langchain-ai/langchain) into Home Assistant.
With this component, users can engage in natural language conversations to control smart devices, create automations, and more.

## Features
- **Conversational Control**: 

  Use natural language to interact with your smart home. Simply chat with your Home Assistant using voice or text commands to perform actions like turning on lights, adjusting thermostat, or creating automation rules.
- **Contextual Understanding**: 

  Utilizing LangChain's memory capability enables this component to understand the context of the conversation and complete some follow-up conversations.
- **Multi LLM Support**

  Based on LangChain's ability, this component will be able to support a variety of large models in the future, including locally deployed models, which will avoid users' concerns about privacy.

## Currently Supported LLM
- **OpenAI**
- [**Tongyi**](https://tongyi.aliyun.com/) (slower response)
- [**Qianfan**](https://cloud.baidu.com/product/wenxinworkshop)

## Currently Supported Abilities In Homeassistant
- call a service, including triggering a scene
- add an automation
- add a script
- add a scene

  ...

## Installation
1. Copy `llm_conversation_assist` folder into `<your config directory>/custom_components`.
2. Restart Home Assistant to load the component

## Configuration
1. Open the Home Assistant frontend or mobile app.
2. Navigate to **Settings** > **Devices&services**.
3. Select **llm_conversation_assist** in **Integrations** tab.
4. Click **ADD SERVICE** and follow config flow to complete the setup.
   - configure necessary settings of the llm model
   - specify config name `<your agent name>`
5. Navigate to **Settings** > **Voice Assistants**.
6. Click **Add assistant**
   - specify assistant name `<your assistant name>`
   - choose `<your agent name>` as Conversation agent

## Usage
1. Open the Home Assistant frontend or mobile app.
2. Click on the conversation agent icon or open the conversation agent panel.
3. Select your assistant by switching to  `<your assistant name>`
4. Now start your conversation

## Debug
### [Get Debug Logs](https://www.home-assistant.io/integrations/logger)

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.llm_conversation_assist: debug
```

> [⚙️ Configuration](https://my.home-assistant.io/redirect/config) > [⚙️ System](https://my.home-assistant.io/redirect/system_dashboard) > [✍️ Logs](https://my.home-assistant.io/redirect/logs)

## Common issues
### 1. Failed to install this component
Most likely caused by the failure to install python dependency packages.
- If the llm you want to use does not depend on this python package, you can just delete the corresponding package name in `manifest.json`.
  - OpenAI -> `langchain-openai`
  - Tongyi -> `dashscope`
  - Qianfan -> `qianfan`
- You can also manually install the corresponding dependencies via `pip install`