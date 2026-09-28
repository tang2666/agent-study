"""探针：带 tools 时，思考模式的开关行为和 tool_choice / reasoning_content 回传。

要钉死三件事（都直接决定 02-tool-calling 骨架里注释怎么写）：

  A. 带 tools 的请求，**不传任何** thinking 参数 → 有没有 reasoning_content？
     （第一章 04/05 的结论是「没有，思考不是默认开的」；根 README 约定 2
       却写「默认就是开的」。带 tools 时会不会不一样？）
  B. 只传 reasoning_effort="high"（不传 extra_body）→ 有没有？
  C. 显式 extra_body={"thinking":{"type":"enabled"}} → 有没有？

  D. 思考开着 + tool_choice="required" → 是不是真的 400？
  E. 思考开着 + tool_choice={"type":"function",...} → 是不是真的 400？

  F. 第二轮不带 reasoning_content（自己拼 dict）→ 是不是真的 400？
  G. 第二轮用 messages.append(message 对象)（自带 reasoning_content）→ 通不通？

这七条跑完，README 里哪些话是真的、哪些是抄来的，就清楚了。
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
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                },
                "required": ["city"],
            },
        },
    },
]


def probe_reasoning(extra: dict, label: str) -> None:
    """发一次带 tools 的请求，报告 reasoning_content 在不在。"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
            tools=TOOLS,
            **extra,
        )
    except Exception as e:  # noqa: BLE001
        print(f"{label}: 抛异常 {type(e).__name__}: {str(e)[:160]}")
        return

    msg = resp.choices[0].message
    has = hasattr(msg, "reasoning_content")
    rc = getattr(msg, "reasoning_content", None)
    rc_len = len(rc) if rc else 0
    n_calls = len(msg.tool_calls) if msg.tool_calls else 0
    print(
        f"{label}: reasoning_content 属性存在={has} 长度={rc_len} "
        f"| tool_calls={n_calls} | finish_reason={resp.choices[0].finish_reason}"
    )


def probe_tool_choice(extra: dict, choice: object, label: str) -> None:
    """思考开/关下试各种 tool_choice，看是不是 400。"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
            tools=TOOLS,
            tool_choice=choice,
            **extra,
        )
        msg = resp.choices[0].message
        n_calls = len(msg.tool_calls) if msg.tool_calls else 0
        print(f"{label}: OK tool_calls={n_calls} content={(msg.content or '')[:40]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: {type(e).__name__}: {str(e)[:200]}")


def probe_echo_back(thinking_extra: dict, drop_reasoning: bool) -> None:
    """第二轮：把上一轮的 assistant message 发回去，看漏掉 reasoning_content 会不会 400。

    drop_reasoning=True  = 自己拼 dict，只带 content + tool_calls（模拟"忘了回传"）
    drop_reasoning=False = 直接 append message 对象（自带 reasoning_content）
    """
    first = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "北京现在天气怎么样？"}],
        tools=TOOLS,
        **thinking_extra,
    )
    msg = first.choices[0].message
    call = msg.tool_calls[0]

    if drop_reasoning:
        assistant_msg = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
            ],
        }
        label = "F 漏传 reasoning_content"
    else:
        assistant_msg = msg
        label = "G 原样 append message 对象"

    messages = [
        {"role": "user", "content": "北京现在天气怎么样？"},
        assistant_msg,
        {"role": "tool", "tool_call_id": call.id, "content": "28°C，晴"},
    ]

    try:
        second = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, **thinking_extra
        )
        print(f"{label}: OK → {(second.choices[0].message.content or '')[:60]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    print("=== 思考模式开关（带 tools） ===")
    probe_reasoning({}, "A 什么都不传")
    probe_reasoning({"reasoning_effort": "high"}, "B 只传 reasoning_effort")
    probe_reasoning(
        {"extra_body": {"thinking": {"type": "enabled"}}}, "C 显式 enabled"
    )

    print("\n=== tool_choice（思考开 vs 关） ===")
    on = {"extra_body": {"thinking": {"type": "enabled"}}}
    probe_tool_choice(on, "required", "D1 required + 思考开")
    probe_tool_choice({}, "required", "D2 required + 思考关")
    probe_tool_choice(
        on,
        {"type": "function", "function": {"name": "get_weather"}},
        "E1 指定工具 + 思考开",
    )
    probe_tool_choice(
        {},
        {"type": "function", "function": {"name": "get_weather"}},
        "E2 指定工具 + 思考关",
    )

    print("\n=== reasoning_content 回传（思考开） ===")
    probe_echo_back(on, drop_reasoning=True)
    probe_echo_back(on, drop_reasoning=False)
