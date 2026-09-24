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

**Python 版本**：>= 3.10。官方 `anthropic` SDK 1.x 要求 3.10 起，低于这个版本会装到旧版，很多新特性（结构化输出、自适应思考）没有。

```bash
python --version
```

**虚拟环境**（推荐 `uv`，不习惯就用 `venv`）：

```bash
# 方式一：uv（快）
uv venv
source .venv/Scripts/activate      # Windows Git Bash

# 方式二：venv
python -m venv .venv
source .venv/Scripts/activate
```

**装 SDK**：

```bash
pip install anthropic
```

**API Key**：设置环境变量 `ANTHROPIC_API_KEY`。不要把 key 写进代码、不要提交到 git。

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

如果所在网络环境需要走网关，SDK 支持 `ANTHROPIC_BASE_URL` 环境变量指向自己的端点，代码不用改。

> 每个目录里都放一个 `.env.example` 记录需要哪些环境变量，真实的 `.env` 不要提交。

---

## 贯穿全程的几条约定

这些在后面的目录里会反复出现，先立在这里：

1. **模型统一用 `claude-opus-5`**。写死在一个 `config.py` 或环境变量里，别散落在各处。
2. **要流的就用流式**。`max_tokens` 大（比如 64000）时必须流式，否则会撞 HTTP 超时。
3. **思考模式默认开着**，用 `thinking={"type": "adaptive"}`。注意 `budget_tokens` 这个参数在当前模型上已经被移除，传了会报 400 —— 老教程里到处都是它，别照抄。
4. **别用 assistant prefill**（把 assistant 消息放最后来"引导开头"）。这个技巧在当前模型上已经移除，会报 400。老教程同样到处都在教。
5. **拿到 tool 的输入一定要 `json.loads()`**，不要对原始字符串做匹配。
6. **错误处理写具体异常链**，不要一把抓 `except Exception`。至少区分 `RateLimitError`（该退避重试）和 `APIStatusError` 400（重试没用）。

---

## 参考的路线来源

- [SocFeng/ai-agents-from-zero](https://github.com/SocFeng/ai-agents-from-zero) — 中文系统教程，覆盖 LangChain / LangGraph / MCP / RAG
- [EldonZhao/ai-agent-startup](https://github.com/EldonZhao/ai-agent-startup) — 8 阶段路线，主张"脚本 → 服务 → 框架 → 工程化"
- [codejunkie99/agent-roadmap-2026](https://github.com/codejunkie99/agent-roadmap-2026) — 英文路线，强调"框架放后面"
- [阿里云 Agent 全栈进阶路线](https://developer.aliyun.com/article/1754230)
- [腾讯云 Agent 开发学习指南](https://cloud.tencent.cn/developer/article/2662031)
