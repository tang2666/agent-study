# 00 — 调通 LLM API

> **接口去哪查**：本目录每个 `.py` 文件**顶部的 docstring**里都有一段 `--- 关键 API ---`，
> 写了这一节用得上的调用形状、字段和坑。这份 README 只给要求和验收标准，不给接口。
> 官方文档入口见根 README 的「官方文档在哪」。

## 要搞懂什么

这一层不是"学会调用接口"，而是**搞清楚一次请求里到底发生了什么**。后面所有 Agent 的问题，最终都会回到这几个概念上。

- **无状态**：API 不记得你上一句说了什么。"多轮对话"是你每次把全部历史重新发一遍实现的。这一点如果没真正理解，写 Agent 时一定会出诡异的 bug
- **token**：输入和输出都按 token 计费，上下文窗口也是按 token 算的。注意 DeepSeek **没有** `count_tokens` 这类接口，只能靠官方离线 tokenizer 或字符比例估
- **流式 vs 非流式**：流式里"思考过程"和"正文"是**两条独立的流**，不是一条
- **采样参数**：`temperature` / `presence_penalty` / `frequency_penalty` 在思考模式下**不报错但完全无效**；`top_p` 反过来只在思考模式下有效。这是个重要的认知更新
- **思考模式**：默认开着，用 `thinking` + `reasoning_effort` 控制
- **结构化错误**：不同错误该怎么处理

## 要写的代码

```
00-hello-llm/
├── config.py             # 已给你（client + MODEL）
├── 01_first_call.py      # 最小可用调用
├── 02_streaming.py       # 流式输出
├── 03_multiturn.py       # 手动维护对话历史
├── 04_tokens.py          # token 计数与成本估算
└── 05_errors.py          # 错误处理
```

**`01_first_call.py`**

一次非流式调用，打印回复文本。

验收：
- [ ] 能跑出结果
- [ ] 打印完整的 `response`，肉眼看清 `choices[0].message.content` / `reasoning_content` / `usage` / `finish_reason` / `model` 这几个字段长什么样
- [ ] 能说出 `finish_reason` 的 6 个可能取值，各自什么含义

**`02_streaming.py`**

改成流式，逐块打印。

验收：
- [ ] 文字是"流"出来的，不是一次性出现
- [ ] **把思考过程和正文分两行分别实时打印**，观察两者的先后顺序
- [ ] 从最后一个 chunk 拿到 `usage`，并打印出来
- [ ] 写完对比一次：同一句话，流式和非流式拿到的 `usage` 一样吗？

**`03_multiturn.py`**

实现一个命令行多轮对话。

验收：
- [ ] 至少能连续聊 5 轮，且模型记得第 1 轮说的内容
- [ ] 代码里有一个 `messages` 列表，每轮**手动** append 用户消息和助手回复
- [ ] 打印 `len(messages)`，观察它每轮怎么涨
- [ ] 能回答："如果把 `messages` 清空，模型还记不记得？为什么？"

**`04_tokens.py`**

在发请求前估算输入长度。

验收：
- [ ] 能对一段文本估算 token 数（用字符比例：英文 ≈ 0.3/字符，中文 ≈ 0.6/字符）
- [ ] 拿真实响应的 `usage` 跟你的估算对比，看差多少
- [ ] 结合 `deepseek-flash` 定价，算出这次调用花多少钱（注意**区分缓存命中/未命中**，差价 50 倍）
- [ ] 跑 10 轮对话后，算出"因为历史不断变长，第 10 轮比第 1 轮贵了几倍"

**`05_errors.py`**

构造几种失败：key 错误、模型名错误、参数非法、触发限流。

验收：
- [ ] 用**具体的异常类**分别捕获，不要一个 `except Exception` 全接
- [ ] 对限流做指数退避重试（1s → 2s → 4s）
- [ ] 对 400 类错误**不要**重试，直接报错退出
- [ ] 能说出哪些错误重试有意义、哪些没有

## 刻意不用的东西

- **不用任何框架**。这一层只用官方 `openai` SDK，看清楚原始形状
- **不用 `langchain` 之类的封装**。先用原生 SDK 建立认知，封装层会把这些概念藏起来
- **不用 `response.choices[0].message.content` 之外的花哨取法**。这一章的目标就是把原始结构看清楚

## 踩坑提醒

- **`temperature` 是个假旋钮**。思考模式下你传它不会报错，但也完全没有效果。想"让输出更稳定"得用别的手段
- **`max_tokens` 可以不传**。不传时默认 8K（非思考）/ 64K（思考），`reasoning_effort=max` 时 128K。上限 384K
- **思考模式下 `content` 可能是空的**，而 `reasoning_content` 有一大段。这不是 bug，是模型还在想。写代码时别假设 `content` 一定非空
- 老教程里的 `thinking={"type":"enabled","budget_tokens":10000}` 是 **Claude** 的写法，DeepSeek 不认 `budget_tokens`。DeepSeek 是 `reasoning_effort`

## 自测问题

答不上来就别往下走：

1. 为什么第二轮对话时你什么都没做，模型就知道上一轮说了什么？
2. 对话到第 50 轮时，每次请求都会变贵。贵在哪里？有哪几种办法缓解（先各说一个方向就行）？
3. `finish_reason` 是 `length` 代表什么？这时候的回复能直接用吗？
4. 流式响应里，`reasoning_content` 和 `content` 为什么要分开处理？
