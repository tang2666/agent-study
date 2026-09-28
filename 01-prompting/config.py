"""把 00-hello-llm/config.py 转发到本目录。

各章的练习脚本统一写 `from config import MODEL, client`（跟 00 一样），
但真实的那份配置**只有一份**，在 00-hello-llm/config.py（model 名、BASE_URL、
API Key 的加载、UTF-8 修正都在那儿），后面所有章节都从它 import，不再各配一套。

问题是 `uv run 01-prompting/xx.py` 运行时，`sys.path[0]` 是 `01-prompting`，
Python 找不到隔壁目录的 `config.py`。本文件就是那座桥：按**路径**把真正的
那份加载进来，再把它导出的名字搬到本模块上。

有了它，本目录的脚本就能照 00 的样子写：

    from config import MODEL, client

而不必在每个练习文件顶部手动折腾 sys.path。
"""

import importlib.util
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "00-hello-llm" / "config.py"

_spec = importlib.util.spec_from_file_location("_hello_llm_config", _CONFIG_PATH)
_real_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_real_config)

BASE_URL = _real_config.BASE_URL
MODEL = _real_config.MODEL
client = _real_config.client
