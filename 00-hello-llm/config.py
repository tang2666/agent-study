"""共用配置。

根目录 README「贯穿全程的几条约定」第 1 条：模型 ID 只写一次，别散落各处。
以后每个章节都从这里 import，换模型时只改这一行。

DeepSeek 提供的是 **OpenAI 兼容接口**，所以用 openai SDK 连它，
不用 anthropic。（它另有一个 Anthropic 格式端点
https://api.deepseek.com/anthropic，本项目不走那条。）
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------- 编码
# Windows 终端默认 GBK，而 Git Bash / PyCharm / VS Code 的终端都是 UTF-8，
# 于是 Python 打的中文（包括报错信息）全变乱码。
# 这里把标准输出 / 标准错误流强制成 UTF-8，和终端对齐。
#
# 必须在**打印任何东西之前**执行，所以放在模块最上面。
# 之所以不用环境变量 PYTHONUTF8=1：那个必须在 Python 启动前就存在，
# 而本文件是被 import 的，运行时再设已经来不及。
#
# hasattr 判断是必要的：stdout 不一定是文本流 ——
# 重定向到管道、pytest 的捕获、pythonw 下可能是 None，这些情况直接跳过。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

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
# .env 在**仓库根目录**（和 pyproject.toml 同级）。
# 这里显式给绝对路径：无论从哪个目录运行、用 `uv run` 还是 IDE 点运行，
# 都找得到，不依赖 python-dotenv 的自动搜索。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 显式检查一下，省得后面抛一个看不懂的 401。
_api_key = os.environ.get("DEEPSEEK_API_KEY")

if not _api_key or _api_key == "sk-...":
    raise RuntimeError(
        "没找到有效的 DEEPSEEK_API_KEY。\n"
        "把仓库根目录的 .env.example 复制成 .env，填上真实 key：\n"
        "    cp .env.example .env\n"
        "（key 缺失、或还是占位符 sk-...，都会到这里。）"
    )

# 这个 client 只建一次，全项目共用。
client = OpenAI(api_key=_api_key, base_url=BASE_URL)
