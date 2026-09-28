"""探针：带 tools 时，漏回传 reasoning_content 到底会不会 400？

约定 3（根 README）原话："带 tools 时，所有历史轮次的 reasoning_content 必须完整回传，
**包括那些没有发生工具调用的轮次**。不回传，API 直接返回 400。"

但 probe_tool_thinking.py 的 F 组（第一轮调了工具、第二轮漏传 reasoning）**没** 400。
说明触发条件比那句话更窄。这支探针把场景补全，找出到底哪种情况会炸：

  H. 中间某一轮**没有工具调用**（纯文本回复），它的 reasoning_content 漏传 → 400？
  I. 中途那轮带 reasoning 回传 → 通？
  J. 调了工具的那轮漏传 → 通？（= 上面 F，复现一次确认）

顺带把 tool_choice 在"显式关思考"下能不能用验掉（README 说关掉就能跑）：
  K. thinking disabled + tool_choice="required" → OK？
  L. thinking disabled + 指定 function → OK？
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前的实时天气。当用户询问某地天气、温度时使用。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"],
            },
        },
    },
]

ON = {"extra_body": {"thinking": {"type": "enabled"}}}
OFF = {"extra_body": {"thinking": {"type": "disabled"}}}


def to_openai_dict(msg) -> dict:
    """把 message 对象压成"只带 content + tool_calls"的 dict —— 模拟漏传 reasoning。"""
    d: dict = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments},
            }
            for c in msg.tool_calls
        ]
    return d


def call(messages: list, label: str) -> None:
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, **ON
        )
        msg = resp.choices[0].message
        n = len(msg.tool_calls) if msg.tool_calls else 0
        print(f"{label}: OK tool_calls={n} → {(msg.content or '')[:50]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: {type(e).__name__}: {str(e)[:170]}")
    return None


def build_two_turn(drop_reasoning_on_tool_turn: bool, label: str) -> None:
    """第一轮工具调用 → 第二轮纯文本结论，然后**第三轮**再问一句。"""
    m1 = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
        tools=TOOLS,
        **ON,
    ).choices[0].message
    call1 = m1.tool_calls[0]

    a1 = to_openai_dict(m1) if drop_reasoning_on_tool_turn else m1

    m2 = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "北京现在天气怎么样？"},
            a1,
            {"role": "tool", "tool_call_id": call1.id, "content": "28°C，晴"},
        ],
        tools=TOOLS,
        **ON,
    ).choices[0].message
    print(f"  中间轮：tool_calls={len(m2.tool_calls) if m2.tool_calls else 0} "
          f"reasoning={'有' if getattr(m2, 'reasoning_content', None) else '无'}")

    # 第三轮：把中间轮（没有工具调用那轮）漏传 reasoning_content
    m2_dict = to_openai_dict(m2)
    hist = [
        {"role": "user", "content": "北京现在天气怎么样？"},
        a1,
        {"role": "tool", "tool_call_id": call1.id, "content": "28°C，晴"},
        m2_dict,
        {"role": "user", "content": "那上海呢？"},
    ]
    call(hist, f"  {label} → 第三轮")


if __name__ == "__main__":
    print("=== 中间轮（无工具调用）的 reasoning_content 漏传 ===")
    build_two_turn(False, "H 工具轮带、中间轮漏")
    build_two_turn(True, "J 工具轮也漏 + 中间轮漏")

    print("\n=== tool_choice 在显式关思考下 ===")
    for label, choice in [
        ("K1 required + 关思考", "required"),
        ("L1 指定工具 + 关思考", {"type": "function", "function": {"name": "get_weather"}}),
    ]:
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
                tools=TOOLS,
                tool_choice=choice,
                **OFF,
            )
            msg = resp.choices[0].message
            n = len(msg.tool_calls) if msg.tool_calls else 0
            print(f"{label}: OK tool_calls={n}")
        except Exception as e:  # noqa: BLE001
            print(f"{label}: {type(e).__name__}: {str(e)[:170]}")

    print("\n=== 对照：required + 什么都不传 ===")
    try:
        client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
            tools=TOOLS,
            tool_choice="required",
        )
        print("M 什么都不传 + required: OK")
    except Exception as e:  # noqa: BLE001
        print(f"M 什么都不传 + required: {type(e).__name__}: {str(e)[:170]}")
