"""02-4 强制 / 禁止调用工具

目标：`tool_choice` 是你对"模型要不要用工具"这件事的控制权。平时用默认值
（auto，模型自己决定），但在两类场景里你要能强制它：

    · 某些流程里**必须**走工具（比如查订单状态，不许它凭空编）
    · 某些流程里**不许**用工具（比如纯聊天模式，省 token、防乱调）

这一节还有一个**踩坑**任务：`required` 和"指定具体函数"在思考模式下会直接
400。你会撞上这个错，然后学会怎么绕开 —— 这类"参数之间互相打架"的坑，
是真实开发里最费时间的一类，提前撞一次很值。

验收标准（详见 ./README.md）：
  [ ] 用 `tool_choice="none"` 让模型**禁止**调用工具，看它怎么用纯文本回答
  [ ] 用 `tool_choice="required"` 让模型**必须**调用工具
  [ ] 用指定函数的形式强制调用**那一个**工具
  [ ] **踩一次坑再爬出来**：上面两个强制用法在思考模式下都返回 400，
      关掉思考模式再跑，记下两次的报错和成功分别长什么样

--- 关键 API ---

  `tool_choice` 是顶层参数（跟 `tools` 同级）。四个取值：

      tool_choice="auto"      # 默认。模型自己决定调不调
      tool_choice="none"      # 禁止调用，只能文本回答
      tool_choice="required"  # 必须调用某个工具（哪个它自己挑）
      tool_choice={"type": "function", "function": {"name": "get_weather"}}
                              # 必须调用**指定**的那一个

  关思考（用前两个强制用法时**必须**加，否则 400）：

      client.chat.completions.create(
          model=MODEL,
          messages=messages,
          tools=TOOLS,
          tool_choice="required",
          extra_body={"thinking": {"type": "disabled"}},   # ← 关键
      )

--- 实测记录（2026-09-29）---

  1. **`required` 和"指定具体函数"在思考模式下都返回 400**，报错原文：

         BadRequestError: 400 - Thinking mode does not support this tool_choice

     两种写法都炸，报的同一句话。

  2. **"什么都不传"也算思考模式** —— 不传 thinking、直接传
     `tool_choice="required"`，照样 400。因为思考是默认开的（见 01 的实测记录 2）。
     所以你必须**显式**关掉它，不能靠"不传就是关"。

  3. 显式加上 `extra_body={"thinking": {"type": "disabled"}}` 之后，
     `"required"` 和"指定具体函数"两种都能正常跑通（都成功拿到 1 个 tool_call）。

  → 结论：想用这两个强制写法，**关思考不是可选项，是前提**。

--- strict: true 实验 ---

  官方有个 Beta 的严格模式，保证模型传来的参数**严格**符合你的 schema。
  它有两个前提，缺一个都不生效：

      ① `base_url` 换成 https://api.deepseek.com/beta
         （本目录的 config.py 给的是正式端点，你得自己再建一个 client）
      ② **每个** function 定义里都要加 `"strict": true`
         （只加在一个上，那一个生效、别的照旧）

  再加一条会有明显效果的：在 `parameters` 里写 `"additionalProperties": false`，
  禁止模型塞你没定义的字段。

  验证：不开严格模式时，故意把 schema 写得随便一点（比如某个参数没写类型），
  跑几十次，看模型会不会偶尔多塞字段 / 类型不对。开了之后再跑，对比一下。

  还有一个必答的问题：**不开严格模式时，参数可能长成什么样？你的代码该怎么防？**

  官方文档只保证"尽力符合"，所以参数可能是：多了你没定义的字段、
  类型不对（数字给成字符串）、该有的没给、枚举值自创。
  防的办法和 01 章 05 那套一模一样 —— **代码侧校验**：
  解析完 arguments 之后自己检查一遍，不合格就当成一次工具错误发回去
  （`role: "tool"` + 说明哪里不对），让模型改。别指望 schema 替你兜住。

  注意：**`strict: true` 不是"结构化输出的开关"**（那是 `response_format` 的事，
  见 01 章）。它只管**工具参数**这一条路径。

--- 坑 ---

  · **400 不是重试能救的。** 它是请求级的错误 —— 参数组合不被支持，
    重发一百次也一样。这种情况要改代码，不是加重试。
  · **`tool_choice="none"` 别和"不传 tools"混为一谈。** 前者模型**看得到**工具
    但它不能调；后者模型压根不知道有工具。两种输出可能不一样，值得对比一次。
  · **强制调用可能被拒或答非所问。** 你问一个跟工具无关的问题（"你是谁？"）
    却 `required`，模型只能硬调一个工具，结果会很奇怪。这不是 bug，是你在乱指挥。
  · **换 /beta 端点会影响缓存和计费口径。** 只是做实验的话别担心，
    但要知道你换了一个端点。
  · 这一节照旧**不写循环**。

--- 实测记录：四个取值跑下来（2026-09-29）---

  1. **四个取值分两类，分界线是"允许/禁止"还是"强制"：**

         auto / none          → 让不让调，思考模式下**都支持**
         required / 指定函数   → 逼它调，思考模式下**都 400**

     所以"关思考"不是可选操作，是后两个用法的**前提**。注意方向：
     不是思考模式被禁，是**这个参数组合服务端不支持**。

  2. **`none` 不会 400。** 正常返回，`finish_reason="stop"`、`tool_calls=0`，
     模型给了一段纯文本："我无法实时获取北京当前天气，所以不能给你准确的
     '此刻'温度……建议你打开手机自带天气 App / 中国天气网 / 墨迹天气"。
     全程**不提**工具的存在 —— 它看得见 `get_weather` 的 schema，但被禁止调用，
     于是走了"我查不了"这条路。

  3. 两遍对照（`TOOL_CHOICE_CASES` 的第三个字段全 False → 全 True）：
     `required` 和"指定函数"从 400 变成 `finish_reason="tool_calls"`、
     都拿到 1 个 `get_weather({"city": "北京"})`。

  4. 还没做：**`none` vs 不传 `tools`** 的输出对比（第 1 条设想）、
     **强制指定 `get_weather` 但问无关问题**（第 2 条设想）、
     **strict 开关的多塞字段比例**（第 3 条设想，要跑 20 次以上）。

--- 你要做的 ---

  实现 main()：把四种取值都跑一遍，把 400 那两次的报错原文也打印出来
  （别 catch 掉就完事 —— 你要看清它长什么样）。
"""

from openai import BadRequestError

from config import MODEL, client
from tools import TOOLS

QUESTION = "北京现在天气怎么样？"

# (说明, tool_choice 的取值, 这一条要不要关掉思考)
#
# 三条都先设成"不关思考"（False）—— 因为要先撞坑。
# 按实测记录 2，思考是默认开的，所以：
#   · "required" 和"指定函数"这两条**会 400**，那是故意的，先看清报错原文
#   · "none" 会不会 400 我没测过，你跑一下顺便填进"待实测"
# 撞完坑把上面两条的 False 改成 True，再跑一遍 —— 两种情况的输出都留档。
TOOL_CHOICE_CASES = [
    ("none（禁止调用）", "none", False),
    ("required（必须调用）", "required", False),
    ("指定 get_weather", {"type": "function", "function": {"name": "get_weather"}}, False),
]


def probe(label: str, choice: object, disable_thinking: bool) -> None:
    """跑一个 tool_choice 取值，**成功和 400 都原样打印**。

    这里刻意只 catch `BadRequestError`：400 是这一节要看清的主角，
    所以把它逮住打印；其他异常（网络断了之类）照旧往上抛，别一起吞了。

    `disable_thinking` 决定 extra_body 传什么 —— 传 disabled 是真的关掉，
    传 enabled 只是把"本来默认就开着"写明白（见 01 的实测记录 2）。
    """
    extra_body = {"thinking": {"type": "disabled" if disable_thinking else "enabled"}}

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": QUESTION}],
            tools=TOOLS,
            tool_choice=choice,
            extra_body=extra_body,
        )
    except BadRequestError as e:
        print(f"  ✗ 400 {e}")
        return

    msg = resp.choices[0].message
    n = len(msg.tool_calls) if msg.tool_calls else 0
    print(f"  finish_reason={resp.choices[0].finish_reason}  tool_calls={n}")
    for c in msg.tool_calls or []:
        print(f"    → {c.function.name}({c.function.arguments})")
    if msg.content:
        print(f"    content={msg.content[:100]!r}")


def main() -> None:
    """把 `tool_choice` 的几种取值各跑一次，对比输出。

    先按原样跑（三条都不关思考），看 required / 指定函数那两条怎么 400；
    再把它们的"关思考"改成 True 跑第二遍。两次的输出都要留着对比。
    """
    for label, choice, disable_thinking in TOOL_CHOICE_CASES:
        thinking = "关思考" if disable_thinking else "思考开"
        print(f"\n=== {label} | {thinking} ===")
        probe(label, choice, disable_thinking)


if __name__ == "__main__":
    main()
