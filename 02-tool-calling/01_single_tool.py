"""02-1 单工具往返

目标：把"一次完整的工具调用往返"跑通。这是整章的地基 —— 02/03/04 全是在这个
往返上加东西（加第二个工具、加错误处理、加 tool_choice）。

    ① 发请求（带 tools）
         ↓
    ② finish_reason == "tool_calls"      ← 不是 "stop"
       模型说："我要调 get_weather，location=北京"
         ↓
    ③ 你执行 —— 查 EXECUTORS，解析 arguments，调函数
         ↓
    ④ 把结果 append 回去（1 条 assistant + N 条 tool）
         ↓
    ⑤ 再发一次请求
         ↓
    ⑥ finish_reason == "stop"，拿到最终回复

  注意 ② 和 ⑤ 是**两次独立的请求**。这一步没意识到的话，你会以为"模型自己
  接着说了下去" —— 不是的，是你又把完整历史发了一遍，模型才接着说的。

验收标准（详见 ./README.md）：
  [ ] 完整跑通一遍往返，顺序对得上上面那张图
  [ ] 在每一步打印完整的 message，看清 tool_calls 长什么样
      （id / function.name / function.arguments）
  [ ] 确认工具那一轮的 finish_reason 是 "tool_calls"，最后一轮是 "stop"
  [ ] 能回答："tool_call.id 是干什么用的？发回结果时不带这个 id 会怎样？"

--- 关键 API ---

  发请求：

      resp = client.chat.completions.create(
          model=MODEL,
          messages=messages,
          tools=TOOLS,                    # ← 顶层参数，不在 extra_body 里
      )
      msg = resp.choices[0].message
      resp.choices[0].finish_reason       # "tool_calls" | "stop" | ...

  模型那一轮回复的结构：

      msg.content                  # str | None
      msg.reasoning_content        # str | None（思考开着时有）
      msg.tool_calls               # list | None

      for c in msg.tool_calls:
          c.id                     # "call_00_xxx" ← 回结果时要原样带上
          c.type                   # "function"
          c.function.name          # "get_weather"
          c.function.arguments     # '{"location": "北京"}'  ← 是**字符串**

  回填消息，**两步，顺序不能反**：

      messages.append(msg)                     # ① 整个 message 对象
      messages.append({                        # ② 每个调用各一条
          "role": "tool",
          "tool_call_id": c.id,                # 靠它和 ① 里的调用配对
          "content": result,                   # 必须是字符串
      })

--- 坑 ---

  · **`arguments` 是字符串，不是 dict。** 要 `json.loads(c.function.arguments)`
    才拿得到 dict。而且模型**可能给你不合法 JSON** —— 要 try/except，
    别让 JSONDecodeError 把程序直接崩了（这条 03 会专门练）。
  · **`msg.tool_calls` 可能是 None。** 最后一轮它就在，别对 None 迭代。
  · **`content` 和 `tool_calls` 可能同时非空。** 模型可能先说一句"我帮你查一下"
    再调工具，文字部分别丢 —— 直接 append 整个 msg 对象就不会丢。
  · **每个 tool_call 一条 `role:"tool"` 消息**，不要合并成一条。
    这跟 Claude 那套是**相反**的（Claude 要求全塞进一条 user 消息），
    别照搬 Claude 的教程。
  · **别自己拼 assistant dict。** `messages.append(msg)` 那个对象自带
    content / reasoning_content / tool_calls 三样，自己拼极容易漏字段。
    官方文档说带 tools 时漏传 reasoning_content 会 **400**；但 2026-09-29 实测
    三次（工具轮漏传、纯文本轮漏传、两轮都漏）**都没复现**。不管它到底强不强制，
    append 整个对象都是最省事、也一定正确的写法，照这个写就行。
  · **这一章不要写 while 循环。** 就写死"发一次 → 执行 → 再发一次"。
    循环是 03 章的事；这一章你要看清的是那个**往返本身**长什么样。

--- 实测记录（2026-09-29）---

  1. 带 tools 时，工具那一轮的 `finish_reason` 是 `"tool_calls"`；
     第二次请求（带了工具结果）回来才是 `"stop"`。

  2. 思考模式**默认就是开的** —— 工具那一轮的 `msg` 上 `reasoning_content`
     属性一定存在。但**内容可能是空串**：探针那次 65 字，正式跑这次是 `""`。
     所以别假设它非空，取值时写 `getattr(msg, "reasoning_content", None) or ""`。
     想复现"不带思考的纯工具调用"，得显式传
     `extra_body={"thinking": {"type": "disabled"}}`。

  3. `tool_choice="required"` 和"指定具体函数"在思考模式下都会 400
     （`Thinking mode does not support this tool_choice`）——
     那是 04 的事，本节用默认值就行。

--- 你要做的 ---

  实现 main()：按上面那张图把一次往返走完，每一步都打印出来。
"""

import json

from config import MODEL, client
from executors import EXECUTORS
from tools import TOOLS

# 一个问题就够。挑那种**模型必须查工具才能答**的 —— 问"帮我算 20+15-5"
# 或者"北京天气怎么样"，它自己编不出来（或者编了也会想调工具）。
QUESTION = "北京现在天气怎么样？"


def main() -> None:
    """跑一次完整的工具调用往返，每一步都打印。

    动手前先在纸上把 messages 的最终形状画出来：
    一共几条？谁在前谁在后？每条的 role 分别是什么？
    画对了再写代码，比边写边试快得多。
    """
    messages=[]
    messages.append({"role":"user","content":QUESTION})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = resp.choices[0].message
    print(msg.model_dump_json(indent=2))
    print(resp.choices[0].finish_reason )

    messages.append(msg)

    call = msg.tool_calls[0]
    name = call.function.name  # "get_weather"
    args = json.loads(call.function.arguments)  # {"city": "北京"}
    result=EXECUTORS[name](**args)
    messages.append({"role":"tool","tool_call_id":call.id,"content":result})


    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = response.choices[0].message
    print(msg.model_dump_json(indent=2))
    print(response.choices[0].finish_reason )
if __name__ == "__main__":
    main()
