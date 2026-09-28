# Agent 开发学习路线（Python）

> this repository is used to study agent

个人学习仓库。目标：**搞懂 Agent 到底是怎么跑起来的**，而不是"会用某个框架"。

- 语言：Python
- 起点：会写代码，但没调用过 LLM API
- 偏向：手写实现优先，框架放最后
- 原则：**代码全部自己写**。每个目录的 README 只给要求、验收标准和坑，不给答案

---

## 学习顺序

| 目录 | 主题 | 一句话 | 建议投入 |
|---|---|---|---|
| `00-hello-llm` | 调通 API | 知道一次请求里到底发生了什么 | 2-3 天 |
| `01-prompting` | 提示词 & 结构化输出 | 学会把 LLM 的输出变成程序能用的数据 | 3-5 天 |
| `02-tool-calling` | 工具调用 | **LLM 应用 → Agent 的分界线** | 3-5 天 |
| `03-agent-loop` | 手写 Agent 循环 | 自己实现 ReAct，没用任何框架 | 1-2 周 |
| `04-memory` | 记忆 | 让 Agent 跨轮次、跨会话记住东西 | 1 周 |
| `05-rag` | 检索增强 | 把外部知识喂进上下文 | 1-2 周 |
| `06-patterns` | 设计模式 | ReAct / Plan-Execute / Reflection 对比 | 1 周 |
| `07-multi-agent` | 多 Agent | 职责拆分与协作 | 1-2 周 |
| `08-mcp` | MCP 协议 | 自己写一个 server，理解它解决什么 | 1 周 |
| `09-frameworks` | 框架对照 | 回头看 LangGraph，判断它省了你什么 | 1 周 |
| `10-eval` | 评估与可观测 | 让"Agent 变差了"不再是玄学 | 持续 |
| `90-notes` | 笔记 | 论文 / 源码精读 | 穿插进行 |
| `99-sandbox` | 试验田 | 随手乱写，不守规矩 | — |

`00` → `03` 是主干，别跳。`04` 之后可以按兴趣调整顺序，`09` 建议真的放到最后。

---

## 怎么用

每个子目录里都有一个 `README.md`，结构统一：

1. **要搞懂什么** — 概念清单
2. **要写的代码** — 具体到文件名 + 验收标准
3. **刻意不用的东西** — 强制约束，通常是为了让你先撞一次墙
4. **自测问题** — 答不上来就说明还没懂，别往下走

写完一个目录的代码，就在下面 ☐ 里打勾。

### 进度

- [ ] `00-hello-llm`
- [ ] `01-prompting`
- [ ] `02-tool-calling`
- [ ] `03-agent-loop`
- [ ] `04-memory`
- [ ] `05-rag`
- [ ] `06-patterns`
- [ ] `07-multi-agent`
- [ ] `08-mcp`
- [ ] `09-frameworks`
- [ ] `10-eval`

---

## 环境准备

依赖管理用 **uv**：`pyproject.toml` 写依赖，`uv.lock` 锁版本，`.venv` 由 uv 管。

**Python 版本**：>= 3.10。官方 `openai` SDK 3.x 要求 3.10 起，低于这个版本会给你装一个很老的版本，很多新特性没有。

```bash
python --version     # 实测 3.12.2
```

**装 uv**（Windows Git Bash，走清华镜像，几秒）：

```bash
python -m pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple
uv --version
```

**建环境 + 装依赖**：

```bash
uv sync
```

`uv sync` 会建好 `.venv`，按 `uv.lock` 装齐所有依赖（含 dev 工具 ruff）。

**以后加依赖不要用 `pip install`**，统一走 uv，它会同时更新 `pyproject.toml` 和 `uv.lock`：

```bash
uv add <包>            # 运行时依赖 → [project] dependencies
uv add --dev <包>      # 开发工具   → [dependency-groups] dev
uv remove <包>
```

`uv.lock` **要提交进 git** —— 它保证换台机器 `uv sync` 装出一模一样的环境。

**跑脚本**（不用先 activate，`uv run` 自己管环境）：

```bash
uv run 00-hello-llm/01_first_call.py
```

> **国内网络**：uv 的镜像配在**本机全局**（`%APPDATA%\uv\uv.toml`），所有 uv 项目都走清华源，
> 仓库里不用再写一遍。只有「装 uv 本身」那一步需要手动加 `-i`。

**API Key**：从模板复制一份，填上真实 key。不要把 key 写进代码、不要提交到 git。

```bash
cp .env.example .env
# 然后编辑 .env，把 DEEPSEEK_API_KEY 换成 platform.deepseek.com 拿到的真实 key
```

`.env` 已被 `.gitignore` 屏蔽，不会进 git。**不用再 export** ——
`00-hello-llm/config.py` 顶部调了 `load_dotenv()`，会自动加载**仓库根目录**的 `.env`
（用绝对路径定位，所以从哪个目录运行都找得到）。

**中文乱码**：Windows 终端默认 GBK，而 Git Bash / PyCharm 的终端是 UTF-8，于是 Python
打的中文（包括报错信息）全变乱码。**这个已经修好了，你不用做任何事** ——
`00-hello-llm/config.py` 开头把 stdout / stderr 强制成了 UTF-8。

> **为什么用代码而不是环境变量**：`PYTHONUTF8=1` 必须在 Python **启动前**就存在，
> 而 `config.py` 是被 import 的，运行时再设来不及。代码里 `reconfigure` 没这个限制，
> 而且跟着仓库走，换台机器也自动生效。

**换个端点**：DeepSeek 有两个端点，我们用的是 OpenAI 格式那个：

| 端点 | 格式 | 本项目 |
|---|---|---|
| `https://api.deepseek.com` | OpenAI 兼容 | ✅ 用这个 |
| `https://api.deepseek.com/anthropic` | Anthropic 格式 | ❌ 不用 |

前者是默认值，写在 `00-hello-llm/config.py` 的 `BASE_URL` 里。
如果所在网络环境需要走自己的网关，改那一行就行。

> 环境变量清单只有根目录的 `.env.example` 一份（记录需要哪些变量），
> 后面所有章节都从 `00-hello-llm/config.py` import `client` 和 `MODEL`，不再各配一套。
> 真实的 `.env` 不要提交。

---

## 贯穿全程的几条约定

这些在后面的目录里会反复出现，先立在这里：

1. **模型统一用 `deepseek-flash`**。写在 `00-hello-llm/config.py` 的 `MODEL` 里，别散落在各处。
   想换 `deepseek-v4-pro` 只改这一行。
2. **思考模式默认就是开的**，不用你传任何参数。默认 effort 是 `high`。
   要关掉得显式传（OpenAI SDK 里必须塞进 `extra_body`）：
   `extra_body={"thinking": {"type": "disabled"}}`。
   **坑在这**：思考模式下 `temperature`、`presence_penalty`、`frequency_penalty`
   这三个参数**静默失效** —— 官方原话是"不会报错，但也没有任何效果"。
   `top_p` 反过来，**只在**思考模式下有效，且有效区间是 **0.95–1.0**
   （传低于 0.95 会被当成 0.95）；非思考模式下它被固定成 1.0，你传的值直接忽略。
   所以"调个温度让输出稳定点"在这个模型上是个假动作。
3. **`reasoning_content` 的回传规则 —— 这条会真的报错，不是风格问题。**
   请求里**带 `tools`** 时，所有历史轮次的 `reasoning_content` **必须完整回传**，
   包括那些**没有发生工具调用**的轮次。官方原文：不回传，API 直接返回 **400**。
   不带 `tools` 时则相反，可以不回传，传了也会被忽略。
   最省事的正确写法是直接 append 整个 message 对象：
   `messages.append(response.choices[0].message)` —— 它自带
   `content` / `reasoning_content` / `tool_calls` 三样，别自己拼 dict 漏字段。
4. **缓存是自动的，不用写代码**。DeepSeek 默认开着**磁盘前缀缓存**，命中就自动降价。
   但**前缀必须完整匹配**才算一个独立单元 —— 所以把稳定的内容
   （system、工具定义、长文档）放前面，会变的内容放后面。顺序反了就永远不命中。
5. **拿到 `tool_calls` 的 `arguments` 一定要 `json.loads()`**。那是个**字符串**，
   不是 dict；而且模型可能给你不合法 JSON，要处理解析失败。
6. **错误处理写具体异常链**，不要一把抓 `except Exception`。
   该重试的：`RateLimitError`(429)、`APIConnectionError`、`APITimeoutError`、
   `InternalServerError`(5xx)。不该重试的：`BadRequestError`(400)、
   `AuthenticationError`(401)、`NotFoundError`(404)、`UnprocessableEntityError`(422)。
   注意它们**全都是 `APIStatusError` 的子类**，所以父类必须写在后面，否则子类分支永远进不去。
   完整对照表见 `00-hello-llm/05_errors.py`。

---

## 官方文档在哪

这个仓库不给答案，所以「接口长什么样」得自己去查。三个来源，可信度从高到低：

**1. 本机装好的 SDK 源码 —— 最准**

仓库锁的是 `openai==3.19.2`，网上教程的版本不一定对得上。要确认某个参数或异常类，直接读本机源码：

```bash
uv run python -c "import openai, os; print(os.path.dirname(openai.__file__))"
```

最常翻的两个文件：

- `_exceptions.py` —— 异常类层次（`05_errors.py` 那张继承表就是从这读出来的）
- `resources/chat/completions/completions.py` —— `create()` 的完整签名（实测 42 个参数）

**2. DeepSeek 官方文档**

| 要查什么 | 地址 |
|---|---|
| Chat Completions 全部参数、响应结构、`finish_reason` 取值 | https://api-docs.deepseek.com/api/create-chat-completion/ |
| 7 个错误码（400 / 401 / 402 / 422 / 429 / 500 / 503） | https://api-docs.deepseek.com/quick_start/error_codes |
| 思考模式（`thinking` / `reasoning_effort`） | https://api-docs.deepseek.com/guides/thinking_mode |
| 定价（含缓存命中差价） | https://api-docs.deepseek.com/quick_start/pricing |
| 入口 / 首次调用 | https://api-docs.deepseek.com/ |

**3. openai SDK 仓库**

- 源码：https://github.com/openai/openai-python
- Chat API reference：https://platform.openai.com/docs/api-reference/chat/create

> 每章 `.py` 文件开头都有一段 `--- 关键 API ---`，把这一章用得上的部分摘了出来。
> 它能帮你起步，但**细节仍以官方文档和实测为准** —— 尤其是少见分支，
> 比如 `finish_reason=aborted`、`402` 落到 `APIStatusError` 这种。

---

## 参考的路线来源

- [SocFeng/ai-agents-from-zero](https://github.com/SocFeng/ai-agents-from-zero) — 中文系统教程，覆盖 LangChain / LangGraph / MCP / RAG
- [EldonZhao/ai-agent-startup](https://github.com/EldonZhao/ai-agent-startup) — 8 阶段路线，主张"脚本 → 服务 → 框架 → 工程化"
- [codejunkie99/agent-roadmap-2026](https://github.com/codejunkie99/agent-roadmap-2026) — 英文路线，强调"框架放后面"
- [阿里云 Agent 全栈进阶路线](https://developer.aliyun.com/article/1754230)
- [腾讯云 Agent 开发学习指南](https://cloud.tencent.cn/developer/article/2662031)
