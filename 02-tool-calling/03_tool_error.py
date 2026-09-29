"""02-3 工具失败的处理

目标：工具是会失败的。学会把"失败"当成一种**正常结果**发回给模型，
而不是让程序崩掉。

核心认知，一句话：

    OpenAI 格式里**没有** is_error 这种字段。
    所谓"工具失败"，就是把错误文本当成 content，用 `role: "tool"` 发回去。

  模型收到的和"工具成功返回一句话"没有任何结构上的区别 —— 它只是读了
  那段文字，然后自己决定怎么办（换个路径重试？换个工具？直接告诉用户？）。

为什么不能让程序崩掉：因为**是模型在决定调什么工具、传什么参数**。
它一定会调出你意想不到的东西 —— 不存在的路径、不存在的工具名、
不合法的 JSON 参数。这些不是"异常情况"，是**常态**。

验收标准（详见 ./README.md）：
  [ ] 工具抛异常时，把错误信息当普通 content 发回去（`role: "tool"`），
      **不要**让程序直接崩
  [ ] 观察模型收到错误后会不会换个方式重试（换个路径、换个参数）
  [ ] 故意给一个永久失败的工具（怎么试都失败），确认模型应对合理，
      且你的程序不会无限转
  [ ] 对比实验：错误信息写详细 vs 只写"失败了"，模型的应对有区别吗？

--- 关键 API ---

  没有新 API，全是普通 Python 的 try/except。要处理的是**三种**失败，
  它们都发生在不同位置，别混成一个：

      ① arguments 不是合法 JSON        → json.loads 那一步炸（JSONDecodeError）
      ② 工具名不存在 / 参数对不上        → 查表或调用那一步炸（KeyError / TypeError）
      ③ 工具自己抛异常                  → 真正执行那一步炸（FileNotFoundError ...）

  三种的处理方式**一样**：变成一条错误文本，配同一个 tool_call_id 发回去。

      try:
          args = json.loads(c.function.arguments)
      except json.JSONDecodeError as e:
          result = f"参数不是合法 JSON：{e}"
      else:
          fn = EXECUTORS.get(c.function.name)       # ← 用 get，别用 []，
          if fn is None:                            #   不然未知工具名直接 KeyError
              result = f"没有名为 {c.function.name} 的工具"
          else:
              try:
                  result = fn(**args)
              except Exception as e:                # ← 这里宽 catch 是**对的**
                  result = f"工具执行失败：{type(e).__name__}: {e}"

      messages.append({"role": "tool", "tool_call_id": c.id, "content": result})

--- 关于那个宽 catch ---

  根 README 约定 6 说"不要一把抓 `except Exception`"。**这里是例外**。

  区别在于位置：约定 6 管的是**网络/API 异常**（那些要按类型决定重不重试）；
  而这里是**信任边界** —— 工具的参数是模型生成的，模型可以传任何东西进来，
  你没法穷举它会怎么把函数打爆。所以这里必须兜住所有异常，
  但**不能吞掉**：异常类型和消息要原样带进 content，让模型看到真实情况。

  反过来说：如果你的 executor 里自己 `except Exception: pass`，
  那就真的是在埋雷了（executors.py 的坑里也提了这条）。

--- 错误信息怎么写（这一节的对照实验）---

  模型是靠你发回去的那段文字来决定下一步的，所以**写多详细是有回报的**。

      ❌ "失败了"
      ✅ "读取失败：FileNotFoundError: 路径 /tmp/x.txt 不存在。
          当前目录可读的文件有：a.txt / b.txt / c.txt"

  后者给了模型"换个路径再试"所需的全部信息，前者它只能放弃或瞎猜。

--- 坑 ---

  · **这一章没有循环，所以"无限转"是你自己造成的。** 你手动重发几轮就几轮。
    真正的步数上限在 03 章 —— 但你现在就该想清楚：模型连着三次请求同一个
    失败的工具，你会怎么办？
  · **别把整个 traceback 塞回去。** 又贵又吵，模型会被栈帧噪声带偏。
    异常类型 + 一句话说明 + 有用上下文，就够了。
  · **别为了让模型"高兴"而编造成功。** 读不到就说读不到。
    你伪造一个成功结果，模型会基于假数据继续往下编，最后给你的答案看着挺像样、
    其实全是错的 —— 这种 bug 最难查。
  · **未知工具名走"未知工具"分支，别 crash。** 模型偶尔会幻觉出你没定义的工具。
  · **`read_file` 的路径要做限制。** 是模型在决定读哪个文件，而你负责真的去读。
    这一节正好让你体会：`tools` 里放什么工具，等于给了模型什么权限。

--- 实测记录（2026-09-29）---

  1. **模型大多数情况不会重试。** 同一组消息（发回去的 content 就是
     `"失败了"`）原样连发 6 次，只有 **2 次**在第二轮发起了新的 tool_calls，
     其余 4 次直接 `finish_reason="stop"`、用文本告诉用户读不到。
     另一组 6 次（第二轮额外带 `reasoning_effort="high"`）是 1/6 ——
     两组差别在噪声范围内，**reasoning_effort 不是原因**。

     → 结论：**"让模型自己从工具失败里恢复"是靠不住的**，它约 3/4 的时候
       根本不试。容错得做在**代码**里（多轮循环、重试策略、步数上限），
       那正是第 3 章的事。这是本节最值钱的一条。

  2. **错误文本详细 vs 简略，看不出稳定差别。** `"失败了"` / 异常原文 /
     "详细 + 列出目录下可读文件" 三种各跑了几次，重试与否都在小样本里摇摆，
     没有哪一条稳定地决定它重不重试。**别拿单次观察当规律** —— 这条自己也适用：
     一度看到"零信息 3/3 重试、列出文件 3/3 放弃"，加大样本后全被推翻。

  3. **一旦它决定重试，是"换个参数形式再探"，不是重复同一个调用。**
     例如第一轮传 `"02-tool-calling/不存在的文件.txt"`（照抄用户原话），
     第二轮换成 `"不存在的文件.txt"`（按 description 的约定去掉目录前缀）。

  4. **它不会编造内容。** 拿到错误后它的回复明确写了"我不想凭空猜测然后给你
     一个编造的答案"，并列出几个可能的方向反问用户。错误信息如实发回去，
     它就如实汇报 —— 这条比"重试率"更让人放心。

  5. 还没做：**永久失败的工具**（第 3 条设想）、**故意写歪 description**
     （第 4 条设想）。这两条留给自己跑。

--- 你要做的 ---

  实现 main()：跑一轮"调工具 → 失败 → 把错误发回去 → 看模型怎么办"。
  建议先写死一个不存在的路径，把链路走通，再做上面的对照实验。
"""

import json

from config import MODEL, client
from executors import EXECUTORS
from tools import TOOLS

# 这句话会引导模型去调 read_file，而下面这个路径**不存在**（故意的）。
QUESTION = "帮我读一下 02-tool-calling/不存在的文件.txt 里写了什么"


def run_tool(call) -> str:
    """执行一个 tool_call，把**任何**失败都变成一段错误文本返回，绝不往上抛。

    三种失败发生在三个不同位置，所以分三层兜：

        ① 参数不是合法 JSON        → json.loads 那一步炸
        ② 工具名不存在 / 参数对不上 → 查表那一步炸
        ③ 工具自己抛异常            → 真正执行那一步炸

    注意 ① ② 发生在**工具被调用之前** —— 工具还没跑起来，它当然兜不住，
    只能由这一层管。三种最后都归一成"一段文本"，配原样的 tool_call_id 发回去：
    OpenAI 格式里没有 is_error 字段，所谓"工具失败"就是 content 里写了错误信息。

    内层那个宽 catch 是**故意**的（根 README 约定 6 的例外）：参数是模型生成的，
    穷举不了它会怎么把函数打爆。但绝不吞掉 —— 异常类型和信息要原样带进 content，
    模型才能据此决定下一步（换路径重试 / 换工具 / 直接告诉你）。
    """
    try:
        args = json.loads(call.function.arguments)
    except json.JSONDecodeError as e:
        return f"参数不是合法 JSON：{e}"

    # 用 get 不用 []：模型偶尔会幻觉出没定义过的工具名，别让它变成 KeyError。
    fn = EXECUTORS.get(call.function.name)
    if fn is None:
        return f"没有名为 {call.function.name} 的工具"

    try:
        return fn(**args)
    except Exception as e:
        return f"工具执行失败：{type(e).__name__}: {e}"


def main() -> None:
    """工具失败 → 把错误当结果发回去 → 观察模型的反应。

    只做一次往返（跟 01 一样），看模型收到错误后会不会自己再试一次；
    如果它再试，**手动**再走一轮，别写循环 —— 步数上限是第 3 章的事。

    想做"详细版 vs 简略版"的对照实验，就把 `run_tool` 最后那行 return
    改成 `return "失败了"` 再跑一遍，对比模型的反应。
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

    # 这一轮模型要调几个工具就处理几个 —— 失败也是"一条正常的结果消息"。
    for call in msg.tool_calls or []:
        result = run_tool(call)
        print(f"→ {call.function.name} 的结果：{result}")
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    response = client.chat.completions.create(
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
