"""00-3 多轮对话（手动维护历史）

目标：亲手体会"API 是无状态的"这件事。
     模型不记得任何东西 —— 是你每次都把全部历史重新发了一遍。

验收标准（详见 ./README.md）：
  [ ] 连续聊 5 轮，模型记得第 1 轮说的内容
  [ ] 有个 messages 列表，每轮手动 append
  [ ] 打印 len(messages)，观察它怎么涨
  [ ] 能回答："清空 messages 会怎样？为什么？"

--- 关键 API ---

    messages = [{"role": "user", "content": "..."}]
    response = client.chat.completions.create(model=MODEL, messages=messages, ...)

    # 把模型的回复追加回历史 —— 直接 append 整个 message 对象
    messages.append(response.choices[0].message)

    # 然后追加下一轮用户输入
    messages.append({"role": "user", "content": "..."})

--- 为什么推荐直接 append 整个 message 对象 ---

  官方文档明说了：response.choices[0].message 自带所有需要的字段，
  下面这两行是**等价**的：

      messages.append(response.choices[0].message)

      messages.append({
          "role": "assistant",
          "content": response.choices[0].message.content,
          "reasoning_content": response.choices[0].message.reasoning_content,
          "tool_calls": response.choices[0].message.tool_calls,
      })

  这一章还没有 tools，所以 reasoning_content 传不传都行（官方说没 tools 时
  传了也会被忽略）。但**请你养成 append 整个对象的习惯** ——
  到 02-tool-calling 和 03-agent-loop 带上 tools 之后，
  reasoning_content 不回传会**直接报 400**。那时候自己拼 dict 漏字段就是自找麻烦。

--- 必做的实验 ---

  找到 append assistant 那行，**注释掉**，再跑一次。
  观察：模型还记不记得上一轮？为什么？
  想明白了再取消注释。这个实验比读十遍文档有用。
"""

from config import MODEL, client


def chat_loop() -> None:
    """命令行多轮对话。

    你要做的：
      1. 建一个 messages 列表，初始为空
      2. 循环读用户输入（input()），按 Ctrl+C 或输入 exit 退出
      3. 每次把用户输入 append 进 messages，发请求，打印回复
      4. 把这一步的回复 append 回 messages
      5. 每轮打印 len(messages)，看清它是怎么涨的
      6. 做完上面的"必做的实验"
    """
    raise NotImplementedError("TODO: 实现 chat_loop()")


if __name__ == "__main__":
    chat_loop()
