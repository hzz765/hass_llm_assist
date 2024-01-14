# LLM Assist For Homeassistant

[English](README.md) | 简体中文

该组件将 [LangChain](https://github.com/langchain-ai/langchain) 的能力集成到 Home Assistant 中。
通过这个组件，用户可以使用自然语言对话来控制智能设备、创建自动化等等。

## 特点
- __对话式控制__: 

  使用自然语言与智能家居进行交互。通过语音或文本命令与 Home Assistant 进行对话，执行诸如打开灯光、调节温度等操作。
- __上下文理解__: 

  利用LangChain的记忆能力使得该组件能够理解对话的上下文，可以完成一些追问对话。
- __支持多种大模型__:

  基于langchain的集成能力，该组件未来将可以支持多种大模型，包括本地部署的模型，这将避免用户对隐私的担忧。