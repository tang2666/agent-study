"""探针：思考模式到底是不是默认开的？**不带 tools**，四种传法对照。

上一支探针（probe_tool_thinking.py）带 tools 跑出来：什么都不传 → reasoning_content
存在 65 字，和显式 enabled 一样。这跟第一章 04/05 的结论（"不是默认开的"）相反。

这支探针把 tools 拿掉，只留四种传法，用 **usage** 加一层证据：
思考真的开着的话，reasoning token 会算进 completion_tokens，数字会明显大。

  1. {}                          什么都不传
  2. {"reasoning_effort": "high"} 只传 effort
  3. thinking disabled            显式关
  4. thinking enabled             显式开

如果 1 ≈ 4 且 3 明显小 → 默认就是开的，第一章的结论要改。
如果 1 和 3 一样 → 第一章是对的，那"带 tools 时会变"本身就是个新发现。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

QUESTION = "某公司有 50 名员工。20 人会游泳，15 人会骑车，5 人两样都会。两样都不会的有几人？"

ARMS = [
    ("1 什么都不传", {}),
    ("2 只传 reasoning_effort", {"reasoning_effort": "high"}),
    ("3 显式 disabled", {"extra_body": {"thinking": {"type": "disabled"}}}),
    ("4 显式 enabled", {"extra_body": {"thinking": {"type": "enabled"}}}),
]


def run(label: str, extra: dict) -> None:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": QUESTION}],
            **extra,
        )
    except Exception as e:  # noqa: BLE001
        print(f"{label}: 抛异常 {type(e).__name__}: {str(e)[:160]}")
        return

    msg = resp.choices[0].message
    has = hasattr(msg, "reasoning_content")
    rc = getattr(msg, "reasoning_content", None) or ""
    u = resp.usage
    print(
        f"{label}: reasoning 属性={has} 长度={len(rc)} "
        f"| content 长度={len(msg.content or '')} "
        f"| completion_tokens={u.completion_tokens} prompt_tokens={u.prompt_tokens}"
    )
    if rc:
        print(f"    reasoning 开头：{rc[:70]!r}")


if __name__ == "__main__":
    for label, extra in ARMS:
        run(label, extra)
