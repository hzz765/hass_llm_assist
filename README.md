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
- [**Tongyi**](https://tongyi.aliyun.com/)
- [**Qianfan**](https://cloud.baidu.com/product/wenxinworkshop)

## Currently Supported Abilities In Homeassistant
- call a service, including triggering a scene
- add an automation
- add a script
- add a scene

  ...