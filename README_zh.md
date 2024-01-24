# LLM Assist For Homeassistant
>MVP (最小可行性产品) 版本, 还有很多可优化的，将逐步改进。
>
>如果有任何想法或建议，可以提issue告诉我

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

## 当前支持的大模型
- **OpenAI**（支持修改api地址）
- [**通义大模型**](https://tongyi.aliyun.com/) （响应速度较慢）
- [**百度千帆（文心一言）**](https://cloud.baidu.com/product/wenxinworkshop)

## 当前支持的Homeassistant能力
- 控制智能家居，包括触发场景
- 新增自动化
- 新增脚本设定
- 新增场景设定

  ...


## 安装

1. 将 `llm_conversation_assist` 文件夹复制到 `<你的配置目录>/custom_components` 目录中。
2. 重新启动 Home Assistant 以加载该组件。

## 配置

1. 打开 Home Assistant 的前端界面或移动应用。
2. 导航到 **设置** > **设备与服务**。
3. 在 **集成** 选项卡中选择 **llm_conversation_assist**。
4. 点击 **添加服务**，然后按照配置流程完成设置。
   - 设置必要的llm模型信息
   - 填写配置名称`<你的代理名称>`
5. 导航到 **设置** > **语音助手**。
6. 点击 **添加助手**
   - 填写助手名称`<你的助手名称>`
   - 选择`<你的代理名称>`作为对话代理

## 使用
1. 打开 Home Assistant 的前端界面或移动应用。
2. 点击对话代理图标或打开对话代理面板。
3. 切换到您的助手，选择`<你的助手名称>`。
4. 开始对话。

## 效果演示
> 对话响应速度与大模型处理速度关系很大，以下视频仅作效果演示参考
- 控制设备
  
https://github.com/hzz765/hass_llm_assist/assets/156523164/54340702-6162-45b9-971e-ee8b3d9a7ca0

- 创建场景

https://github.com/hzz765/hass_llm_assist/assets/156523164/b4007440-25b2-43a5-bb89-a94f227b44f5

- 触发场景

https://github.com/hzz765/hass_llm_assist/assets/156523164/bc3d9c45-a957-4b03-9142-2d1c605dc1a2
  
- 创建自动化

https://github.com/hzz765/hass_llm_assist/assets/156523164/bd2cc717-cd9e-4a02-84a8-e3e58f1a2718

- 日常对话

https://github.com/hzz765/hass_llm_assist/assets/156523164/a82aac47-ad69-4b7d-85f3-a73e3d7eccf3

## 调试
### [获取调试日志](https://www.home-assistant.io/integrations/logger)

```yaml
# 修改 configuration.yaml (需重启)
logger:
  default: info
  logs:
    custom_components.llm_conversation_assist: debug
```

> [⚙️ 配置](https://my.home-assistant.io/redirect/config) > [⚙️ 系统](https://my.home-assistant.io/redirect/system_dashboard) > [✍️ 日志](https://my.home-assistant.io/redirect/logs)

## 常见问题
### 1. 安装/启动失败
这很可能是由于无法安装 Python 依赖包导致的。

- 如果要使用的 LLM 不依赖于此 Python 包，可以在 `manifest.json` 文件中删除相应的包名称。
  - OpenAI -> `langchain-openai`
  - 通义 -> `dashscope`
  - 百度千帆 -> `qianfan`
- 你还可以通过 `pip install` 命令手动安装相应的依赖项。