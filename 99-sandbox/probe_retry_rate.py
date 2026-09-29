"""探针：同一个失败输入，模型重试的概率是多少？reasoning_effort 会不会改变它？

起因：两个人跑同一件事，结论相反 ——
  · 用户的 03_tool_error.py（带 reasoning_effort="high"）→ 发回"失败了"，模型 stop
  · 本目录的 probe_tool_retry.py（不带 reasoning_effort）→ 发回"失败了"，3/3 重试

逐行对比后，唯一的差别是 reasoning_effort。假设：**它是原因**。

做法：第一轮只跑一次拿到 assistant 回复，然后**同一组消息**（一模一样，
包括那条 content="失败了" 的 tool 消息）连发 N 次，数第二轮里
finish_reason == "tool_calls" 的比例。两组唯一的区别是第二轮的 reasoning_effort。

关键点：第二轮的消息完全不变，所以差异只可能来自模型自己的随机性
和 reasoning_effort 这个参数 —— 没有别的变量。

n 很小（每组 6 次），结论只用来判断"两组的差别大到不像噪声"，不是精确概率。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02-tool-calling"))

from config import MODEL, client  # noqa: E402
from tools import TOOLS  # noqa: E402

QUESTION = "帮我读一下 02-tool-calling/不存在的文件.txt 里写了什么"
ERROR_TEXT = "失败了"
N = 6


def decide(messages: list, extra: dict) -> str:
    """发一次第二轮，返回 'tool_calls'（重试）或 'stop'（放弃）。"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        extra_body={"thinking": {"type": "enabled"}},
        **extra,
    )
    return resp.choices[0].finish_reason


def main() -> None:
    first = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": QUESTION}],
        tools=TOOLS,
        reasoning_effort="high",  # 跟用户的脚本对齐
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = first.choices[0].message
    calls = msg.tool_calls
    if not calls:
        print("第一轮没调工具，探针没法继续")
        return
    print(f"第一轮：{len(calls)} 个 tool_call，finish_reason={first.choices[0].finish_reason}")

    # 这条 messages 是两组共用的常量 —— 唯一变量是第二轮的 reasoning_effort
    messages = [{"role": "user", "content": QUESTION}, msg]
    for c in calls:
        messages.append({"role": "tool", "tool_call_id": c.id, "content": ERROR_TEXT})

    for label, extra in [
        ("第二轮不带 reasoning_effort", {}),
        ("第二轮带 reasoning_effort=high", {"reasoning_effort": "high"}),
    ]:
        results = [decide(messages, extra) for _ in range(N)]
        n_retry = results.count("tool_calls")
        print(f"{label}: 重试 {n_retry}/{N}  {results}")


if __name__ == "__main__":
    main()
