# 03 — 手写 Agent 循环

> **整个路线的核心。**
> 这一层做完，你就知道 Agent 是什么了 —— 它不是魔法，是一个 `while` 循环。
> 做完之后回头看任何 Agent 框架，你都能看懂它在干什么。

## 要搞懂什么

- **Agent 的定义**：模型 + 循环 + 工具 + 状态 + 边界。就这五样，没有别的
- **ReAct 循环**：Reasoning → Acting → Observation，一轮一轮转
- **循环的终止**：怎么知道该停了。OpenAI 格式里就一个判断 —— `message.tool_calls is None`
- **循环的边界**（最重要，也是最容易被忽略的）：
  - 最大步数（防止无限转）
  - 超时
  - 成本预算
- **错误恢复**：某一步失败了，是重试、跳过、还是终止
- **状态管理**：循环过程中什么东西需要被记住。**在 DeepSeek 上这一条格外重要，见下**

## 要写的代码

```
03-agent-loop/
├── agent.py            # Agent 循环本体
├── tools.py            # 复用 02 的工具，自己扩展几个
├── main.py             # 命令行入口
└── traces/             # 每次运行保存完整轨迹（JSON）
```

**`agent.py` 的核心结构**

大致是：

```
while 还有步数:
    调用模型（带 tools）
    messages.append(这一轮的 message)      # ← 必须！不是只 append 文本
    如果 message.tool_calls 不是 None:
        逐个执行工具
        每个结果各 append 一条 role="tool" 的消息
        继续循环
    否则:
        返回 message.content
```

这个骨架你自己写，但要满足下面的验收。

## 验收标准

**基础**

- [ ] 能跑通一个需要**至少 3 轮**工具调用才能完成的任务
      （比如"查出北京天气，如果超过 30 度就告诉我该喝什么，否则告诉我该穿什么"，
      并且你故意把"查温度"和"查建议"拆成两个工具）
- [ ] 循环里 `messages` 的拼接是正确的：**先 append 整个 assistant message 对象，
      再为每个工具调用各 append 一条 `role: "tool"` 消息**

**思考模式的硬要求（这一章最容易翻车的地方）**

- [ ] **`reasoning_content` 完整回传**。官方原文：带 `tools` 的请求，
      `reasoning_content` 必须在后续所有请求里完整传回去，
      **包括没有发生工具调用的那些轮次**；不传，**API 直接返回 400**
- [ ] 你用的是 `messages.append(response.choices[0].message)` 这种做法，
      而不是自己拼 dict（自己拼极容易漏掉 `reasoning_content`）
- [ ] **亲手制造一次 400**：故意改成自己拼 dict 且不带 `reasoning_content`，
      看报错长什么样，然后改回来

**边界（必须全做到）**

- [ ] **最大步数上限**，比如 15 步。到了就停止，并明确告诉用户"没做完，因为步数用完了"
- [ ] **超时上限**，比如 120 秒
- [ ] **成本上限**：累加每轮的 token 使用量，超过预算就停。打印花了多少钱
- [ ] 三个上限分别触发一次，确认行为符合预期

**健壮性**

- [ ] 工具抛异常时循环**不崩**，把错误作为 `role: "tool"` 的 content 发回模型
- [ ] 模型连续 N 次调用同一个工具、传同样的参数 → 检测到死循环，打断
      （这是真实 Agent 最常见的失败模式之一）
- [ ] 模型返回了空的 `content`（`tool_calls` 也没有）→ 能识别并处理

**可观测**

- [ ] 每次运行把完整轨迹存成 JSON 到 `traces/`：每轮的输入、模型的原始输出、
      工具调用及结果、耗时、token 数（含缓存命中数）
- [ ] 终端打印每一步的人话日志，比如：
      ```
      [1/15] 模型决定调用 get_weather(city="北京")
      [1/15] 结果：28°C，晴   (耗时 0.3s)
      [2/15] 模型决定调用 get_advice(temp=28)
      [2/15] 结果：穿短袖
      [3/15] 最终答案：...
      ```
- [ ] 跑完之后，光看轨迹文件就能完整复盘这次运行发生了什么

## 刻意不用的东西

- **不用 `langchain` / `langgraph` / `crewai` / 任何 Agent 框架**
- **不用 SDK 的自动循环助手**

  为什么？因为你要先撞一次墙。你要亲身经历这些：
  - **忘了回传 `reasoning_content`，吃一个 400**（DeepSeek 上的头号坑）
  - 忘了把 assistant message 加回 `messages`，模型开始无限重复
  - 工具结果忘了配对 `tool_call_id`，模型答非所问
  - 没设步数上限，跑飞了烧掉几块钱
  - 工具报错没处理，整个程序崩了

  **这些墙撞过一遍，你才会知道框架在替你做什么。** 撞完之后，`09-frameworks` 再去看 LangGraph，那时候你的判断才是有价值的。

- **不用 `print` 当唯一日志**。要能结构化地存下来

## 踩坑提醒

- **头号坑：带 tools 时不回传 `reasoning_content` = 400**。
  最省事的正确做法就是 `messages.append(response.choices[0].message)` ——
  这个对象自带 `content` / `reasoning_content` / `tool_calls` 三样，一个都不漏
- **忘了 append assistant message**：只 append 工具结果不 append 模型的那条回复，
  `messages` 结构就坏了。每轮**两类**都要加（1 条 assistant + N 条 tool）
- **每个工具结果单独一条消息**，`{"role":"tool","tool_call_id":tool.id,"content":...}`。
  不要合并成一条 —— 这跟 Claude 那套是**反过来**的，别照搬 Claude 教程
- **`arguments` 要先 `json.loads()`**。它是字符串，不是 dict；而且可能不合法
- **模型"说完就调工具"**：`message.content` 和 `message.tool_calls` 可能同时非空，
  文字部分也要保留，别丢了
- **成本上限算不准**：工具结果的 token 也算输入。粗略算法是累加每轮的
  `usage.prompt_tokens` + `usage.completion_tokens`。想算准一点，
  输入还要区分 `prompt_cache_hit_tokens`（便宜 50 倍）和 `prompt_cache_miss_tokens`
- **截断的判据变了**：不是 `stop_reason == "max_tokens"`，而是
  `finish_reason == "length"`。这时候的回复不能用，你得处理这个分支
- **循环结束的判据是 `tool_calls is None`**，不是看 `content` 空不空。
  思考模式下 `content` 完全可能是空的而 `tool_calls` 有值

## 自测问题

答不上来说明还没真懂：

1. 用一句话说清 Agent 和"一次 LLM 调用"的区别。
2. 为什么必须有最大步数上限？没有的话最坏会发生什么？
3. 模型为什么会陷入死循环？有哪几种常见触发方式？你打算怎么检测？
4. 如果一个工具连续失败 3 次，你觉得应该继续、换个方式、还是终止？为什么？这个决策该由谁来定 —— 你的代码还是模型？
5. 为什么 DeepSeek 在带 `tools` 时强制要求回传 `reasoning_content`？不带 `tools` 时为什么又不需要？
6. 你现在这个循环，和 LangGraph 的图结构比，缺了什么？（先自己想，`09-frameworks` 再对答案）
