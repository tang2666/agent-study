# 02 — 工具调用（Tool Calls / Function Calling）

> **这是整个路线里最重要的一层。**
> "LLM 应用"和"Agent"的分界线就在这里。前面两层做的是"让模型说话"，从这里开始是"让模型做事"。

## 要搞懂什么

- **工具调用的完整往返**：你定义工具 → 模型决定调用 → 模型**不执行**，只是告诉你它想调什么 → 你执行 → 把结果发回去 → 模型基于结果继续
- **关键认知**：模型永远不会真的执行你的代码。它只是在"请求"你执行。真正跑代码的永远是你的程序。这个认知搞混了，后面所有权限、安全、沙箱的问题都想不明白
- **工具的三要素**：`name`、`description`、`parameters`（JSON Schema）
- **`description` 是最重要的部分**。它决定了模型什么时候会想起来用这个工具。写不好，模型要么不用，要么乱用
- **`arguments` 是个 JSON 字符串**，不是 dict。必须 `json.loads()`，而且要处理解析失败
- **并行调用**：一次回复里可能有多个 `tool_calls`，每个都要**单独**回一条结果
- **工具失败**：OpenAI 格式里**没有** `is_error` 这种字段，错误就是把错误文本塞进 `content` 发回去
- **`tool_choice`**：控制模型是否必须调用工具（**注意它在思考模式下有一半用不了，见下**）

## 要写的代码

```
02-tool-calling/
├── tools.py            # 工具定义（schema）
├── executors.py        # 工具的实际执行逻辑
├── 01_single_tool.py   # 单工具往返
├── 02_multi_tool.py    # 一次往返处理多个工具
├── 03_tool_error.py    # 工具失败的处理
└── 04_tool_choice.py   # 强制 / 禁止调用工具
```

**先写 3 个工具**（自己挑，建议包含一个会失败的）：

- 一个纯计算的，比如 `calculate(expression)`
- 一个查真实数据的，比如 `get_weather(city)`（可以先用假数据）
- 一个会失败的，比如 `read_file(path)` —— 路径不存在时要报错

### 工具的 schema 长什么样（官方形状，照这个写）

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前的实时天气。当用户询问某地天气、温度、是否下雨时使用。",
            "parameters": {                 # ← 叫 parameters，不叫 input_schema
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名，中文或英文均可"}
                },
                "required": ["location"],
            },
        },
    },
]
```

注意外面还包了一层 `{"type": "function", "function": {...}}`。

**`01_single_tool.py`**

验收：
- [ ] 完整跑通一遍往返，正确顺序是：
      发请求（带 `tools`）→ `finish_reason == "tool_calls"` → 执行 → append 工具结果 → 再发一次 → 拿到最终回复
- [ ] **在每一步打印完整的 `message`**，看清 `tool_calls` 长什么样（`id` / `function.name` / `function.arguments`）
- [ ] 确认这一轮的 `finish_reason` 是 `"tool_calls"`，最后一轮是 `"stop"`
- [ ] 能回答："`tool_call.id` 是干什么用的？发回结果时不带这个 id 会怎样？"

**`02_multi_tool.py`**

设计一个会让模型**同时**调用多个工具的问题，比如"北京和上海现在天气怎么样"。

验收：
- [ ] 观察到一次回复里出现**两个** `tool_calls`
- [ ] 你的程序能并发执行它们
- [ ] **每个工具结果各发一条 `role: "tool"` 的消息**，不要合并成一条
      （注意：这跟 Claude 那套是**相反**的。Claude 要求所有结果塞进一条 user 消息；
      OpenAI 格式是一条结果一条消息，靠 `tool_call_id` 配对。别照搬 Claude 的教程）
- [ ] 打印结果消息的条数确认

**`03_tool_error.py`**

让工具失败，看模型怎么应对。

验收：
- [ ] 工具抛异常时，把**错误信息当普通 content** 发回去（`role: "tool"`），**不要**让程序直接崩
- [ ] 观察模型收到错误后会不会换个方式重试（比如换个路径、换个参数）
- [ ] 故意给一个**永久失败**的工具（怎么试都失败），确认模型的应对合理，且你的循环不会无限转
- [ ] 对比实验：把错误信息写详细（带"路径不存在，现有文件有 xxx"）vs 只写"失败了"，模型的应对有区别吗？

**`04_tool_choice.py`**

验收：
- [ ] 用 `tool_choice="none"` 让模型**禁止**调用工具，看它怎么用纯文本回答
- [ ] 用 `tool_choice="required"` 让模型**必须**调用工具
- [ ] 用 `tool_choice={"type":"function","function":{"name":"get_weather"}}` 强制调用**指定**那个工具
- [ ] **踩一次坑再爬出来**：上面两个强制用法在思考模式下都会返回 **400**。
      官方原文："`required` 和指定具体工具的写法在思考模式下不支持，API 会返回 400。
      要先关掉思考模式。" 把思考模式关掉（见 `00-hello-llm` 的约定 2）再跑，
      记录两次的报错和成功分别长什么样

**`strict: true` 实验**

官方有个 Beta 的严格模式，保证模型传来的参数严格符合你的 schema。

验收：
- [ ] 说清楚开启它的**两个**前提：`base_url` 要换成 `https://api.deepseek.com/beta`，
      并且**每个** function 都要设 `"strict": true`
- [ ] 在 schema 里加上 `"additionalProperties": false`，观察模型输出是否更规矩
- [ ] 能说出：不开严格模式时，参数可能长成什么样？你的代码该怎么防？

## 刻意不用的东西

- **不用框架的 tool 装饰器**（比如 `@tool`）。手写 schema，你才知道框架替你生成了什么
- **不用任何自动循环助手**。这一层要自己写那一次往返，`03-agent-loop` 里才把循环补上
- **不用强制插入工具调用的高级玩法**。官方明确说了：**Chat Completion API 不支持**
      在对话中间插入工具调用（Anthropic API 和 Responses API 才支持）。
      知道有这条边界就行，别在这上面浪费时间

## 踩坑提醒

- **`arguments` 是字符串，不是 dict**。官方示例里是 `json.loads(tool.function.arguments)`。
      而且模型可能给你不合法 JSON —— 要 try/except，解析失败就当成一次工具错误发回去
- **每个工具结果单独一条消息**。`{"role":"tool","tool_call_id":tool.id,"content":...}`，
      一条一个，靠 id 配对。不要合并
- **`tool_calls` 和 `content` 可能同时存在**。模型的回复里可能既有文字又有工具调用，
      文字部分也要保留（直接 append 整个 message 对象就不会丢）
- **带 `tools` 时，`reasoning_content` 必须完整回传，否则 400**。这是全局约定 3。
      最省事的做法：`messages.append(response.choices[0].message)`，别自己拼 dict 漏字段
- `name` 只能用字母数字下划线，别用中文名
- `description` 要写"什么时候用它"，不是"它是什么"。对比：
  - ❌ `"获取天气"` — 模型不知道什么情况下该用
  - ✅ `"查询指定城市当前的实时天气。当用户询问某地天气、温度、是否下雨时使用。输入城市名，中文或英文均可。"`

## 自测问题

1. 模型返回 `tool_calls` 之后，谁真正执行了那个工具？这个区分为什么重要？
2. 为什么 `description` 比 `parameters` 的 schema 更能决定工具被正确使用？
3. 一次回复里出现两个 `tool_calls`，你能合并成一条消息发回结果吗？为什么不能？
4. 工具失败了，是让程序抛异常，还是把错误当结果发回给模型？各自的后果是什么？
5. `tool_choice="required"` 为什么在思考模式下用不了？这个限制说明了什么？
