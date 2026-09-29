"""02-2 一次往返处理多个工具

目标：模型**一次回复**里可能返回好几个 tool_calls。学会怎么正确处理一批，
而不是只处理第一个。

跟 01 的差别只有一处 —— 01 里 `msg.tool_calls` 长度是 1，这里是 N。
但就是这一处差别，会带出三个新问题：

    ① 结果要发几条？        → N 条，每个调用各一条
    ② 能不能合并成一条？    → 不能（跟 Claude 相反，详见"坑"）
    ③ 能不能并发执行？      → 能，而且应该（N 个工具串行跑，延迟就是 N 倍）

验收标准（详见 ./README.md）：
  [ ] 观察到一次回复里出现**两个** tool_calls
  [ ] 你的程序能并发执行它们
  [ ] **每个工具结果各发一条 `role: "tool"` 的消息**，不要合并成一条
  [ ] 打印结果消息的条数确认

--- 关键 API ---

  跟 01 完全一样，唯一的新东西是 `tool_calls` 的长度：

      msg.tool_calls                  # list，长度可能是 1，也可能是 N
      # 这一节要构造出 N == 2 的情况

      for c in msg.tool_calls:        # 逐个执行、逐个 append
          ...
          messages.append({"role": "tool", "tool_call_id": c.id, "content": r})

  并发执行可以用标准库，不用装东西：

      from concurrent.futures import ThreadPoolExecutor
      # 或者更简单的：并发跟串行的**结果**是一样的，
      # 先串行跑通，确认 messages 形状对了，再换成并发的去体会差别

  **别改 messages 的顺序**：不管你怎么并发执行，append 的时候
  建议还是按 `msg.tool_calls` 的原始顺序来。

--- 怎么让模型一次调两个工具 ---

  一句话里问两件事就行，比如"北京和上海现在天气怎么样"。模型大概率会在
  同一轮里返回两个 tool_calls —— 但**不是保证**。它也可能只查一个、
  等结果回来再查第二个（那就是 03 章那种多轮往返了）。

  跑几次，观察它到底是一次给两个，还是分成两轮。这个行为本身就是个知识点。

--- 坑 ---

  · **不能合并成一条消息。** OpenAI 格式是「一个工具结果一条 `role:"tool"` 消息」，
    靠 `tool_call_id` 跟请求配对。Claude 那套（所有结果塞进一条 user 消息）
    在这里**不成立** —— 别把两家的教程混着看。
  · **`tool_call_id` 必须和请求里的 `c.id` 完全一致。** 写错 / 漏写，
    模型会答非所问或者干脆不认。这也是 01 那句自测题的答案。
  · **别只处理 `msg.tool_calls[0]`。** 这是最常见的 bug：单工具时能跑通，
    一遇到并行调用就少发了几条结果，模型于是收到一堆残缺上下文。
  · **`arguments` 还是字符串**，每个都要自己 `json.loads()`。
  · **别在这个文件里写 while 循环。** 如果模型分了两轮才查完两个城市，
    你就手动再走一轮 —— 循环是 03 章的事。

--- 待实测（跑完把观察填进来）---

  1. 一次回复里真的给了两个 tool_calls 吗？还是分了两轮？
     换个问法（比如"分别" / "顺便" / "两个都"）会不会改变它的行为？

  2. 并发执行 N 个工具，总耗时和串行比差多少？（在 executor 里 sleep 一下
     就看得出来，不然本地函数太快，看不出差别）

  3. 把结果消息的**顺序打乱**再发回去，模型还能正确配对吗？
     （OpenAI 说是靠 id 配对，但值得亲手验一次）

  4. 故意少发一条结果（只发第一个工具的），模型会怎么样？会报 400 吗？

--- 你要做的 ---

  实现 main()：构造一个能触发并行调用的问题，两个工具都执行，
  结果各发一条，确认最终答案是完整的。
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from config import MODEL, client
from executors import EXECUTORS
from tools import TOOLS

# 挑一个**天然需要查两个东西**的问题。
# 只能说"北京和上海"这种并列问法，才容易一次触发两个 tool_calls；
# 问成"先查北京再查上海"它就会老老实实分两轮。
QUESTION = "北京和上海现在天气怎么样？"


def run_one(tool_call) -> tuple[str, str]:
    """执行**一个** tool_call，返回 (tool_call_id, 结果字符串)。

    为什么要拆成单独一个函数？因为它要被丢进线程池、在**别的线程**里跑。
    在这种函数里不能碰 `messages` —— 多个线程同时 append 一个 list 是竞态，
    顺序和内容都可能乱。所以它只干一件事：给我一个调用，还你一个结果。
    往 `messages` 里塞，是主线程的事。

    这里能安全并发，根本原因是这三个 executor **没有共享可变状态**：
    它们只读自己的入参、返回一个字符串。带共享状态的函数不能这么扔进线程池。

    注意：这里没做错误处理，工具一抛异常整个 `list(pool.map(...))` 就会炸。
    把失败变成"发给模型的错误结果"是 03 章的事。
    """
    args = json.loads(tool_call.function.arguments)
    return tool_call.id, EXECUTORS[tool_call.function.name](**args)


def main() -> None:
    """跑一次并行工具调用，确认结果消息的条数 == tool_calls 的条数。

    先在纸上想清楚：如果这一轮有 2 个 tool_calls，`messages` 最终会比
    01 那种单工具的情况多几条？
    """
    messages = []
    messages.append({"role": "user", "content": QUESTION})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = resp.choices[0].message
    print(msg.model_dump_json(indent=2))
    print(resp.choices[0].finish_reason)
    messages.append(msg)

    # 这一轮模型要调几个工具。先判空 —— 模型如果直接给了答案，
    # tool_calls 会是 None，对 None 迭代直接 TypeError。
    calls = msg.tool_calls or []
    print(f"这一轮有 {len(calls)} 个 tool_calls")

    started = time.perf_counter()
    # pool.map 的关键性质：**返回顺序 == 输入顺序**，跟谁先跑完无关。
    # 所以 results 和 calls 是一一对应的，顺序不会乱。
    # `with` 离开时自动关池并等所有线程结束（相当于 join），不用手动 shutdown。
    with ThreadPoolExecutor() as pool:
        results = list(pool.map(run_one, calls))
    print(f"{len(calls)} 个工具执行完，耗时 {time.perf_counter() - started:.3f}s")

    # append 的顺序按 calls 的原始顺序来 —— 结果顺序虽然不影响 id 配对，
    # 但保持稳定顺序，打印出来好看，也少一个变量。
    for call_id, result in results:
        messages.append({"role": "tool", "tool_call_id": call_id, "content": result})

    # 条数对账：1 条 user + 1 条 assistant + N 条 tool。
    # 这就是本节验收标准里"确认结果消息条数 == tool_calls 条数"那一条。
    print(f"messages 现在 {len(messages)} 条（1 user + 1 assistant + {len(calls)} tool）")

    response=client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = response.choices[0].message
    print(msg.model_dump_json(indent=2))
    print(response.choices[0].finish_reason)
if __name__ == "__main__":
    main()
