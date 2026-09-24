"""共用配置。

根目录 README「贯穿全程的几条约定」第 1 条：模型 ID 只写一次，别散落各处。
以后每个章节都从这里 import，换模型时只改这一行。

DeepSeek 提供的是 **OpenAI 兼容接口**，所以用 openai SDK 连它，
不用 anthropic。（它另有一个 Anthropic 格式端点
https://api.deepseek.com/anthropic，本项目不走那条。）
"""

import os

from openai import OpenAI

# ---------------------------------------------------------------- 模型
# 官方定价页（api-docs.deepseek.com/quick_start/pricing）当前的两个模型：
#
#   deepseek-flash     DeepSeek-V4.1-Flash    便宜，1M 上下文。学习够用
#   deepseek-v4-pro    DeepSeek-V4-Pro-0813   更强，价格约 4 倍
#
# 旧名字 deepseek-v4-flash 仍被接受，但对应模型已退役，
# 请求实际由 V4.1-Flash 服务，并按 Flash 价格计费。别再用了。
MODEL = "deepseek-flash"

BASE_URL = "https://api.deepseek.com"

# ---------------------------------------------------------------- client
# 显式检查一下，省得后面抛一个看不懂的错。
# 这里**不会**自动读 .env 文件 —— 环境变量得真的存在。
# 要不要用 python-dotenv 让 .env 生效，见根 README 的说明。
_api_key = os.environ.get("DEEPSEEK_API_KEY")

if not _api_key:
    raise RuntimeError(
        "没找到环境变量 DEEPSEEK_API_KEY。\n"
        "先在当前终端里设置（Git Bash）：\n"
        '    export DEEPSEEK_API_KEY="sk-..."\n'
        "注意：光把 key 写进 .env 文件是不生效的，Python 不会自动读它。"
    )

# 这个 client 只建一次，全项目共用。
client = OpenAI(api_key=_api_key, base_url=BASE_URL)
