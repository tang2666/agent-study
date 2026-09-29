"""探针：工具失败后，模型到底会不会重试？重试与否由什么决定？

背景：跑 03_tool_error.py 时观察到 —— 工具失败、把错误发回去之后，
模型的 finish_reason 始终是 "stop"，从来不发起第二次 tool_calls。

要钉死的问题是：这是模型的固有限制，还是**我们写的错误文本**造成的？

做法：第一轮固定不变（问它读一个不存在的文件），拿到同一个 assistant 回复后
**复制成四份**，只有"发回去的错误文本"不一样，再看第二轮：

    ① "失败了"                     —— 零信息
    ② 详细但无出路（只有异常类型）    —— 就是 03 现在的详细版
    ③ 详细 + 列出可读文件            —— 给了模型一条"可走的路"
    ④ "服务暂时不可用，请稍后重试"    —— 看起来"再试一次就好"

判据：第二轮 finish_reason == "tool_calls" 就是重试；"stop" 就是放弃。

第一轮只跑一次、四份共用 —— 这样唯一的变量就是错误文本，
不然模型自己的随机性会把结论搅浑。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02-tool-calling"))

from config import MODEL, client  # noqa: E402
from tools import TOOLS  # noqa: E402

QUESTION = "帮我读一下 02-tool-calling/不存在的文件.txt 里写了什么"

# (标签, 发回给模型的错误文本)
ERROR_VARIANTS = [
    ("① 零信息", "失败了"),
    (
        "② 详细无出路",
        "工具执行失败：FileNotFoundError: [Errno 2] No such file or directory: "
        "'C:\\baidunetdiskdownload\\practice\\02-tool-calling\\不存在的文件.txt'",
    ),
    (
        "③ 详细 + 列出可读文件",
        "读取失败：路径 不存在的文件.txt 不存在。"
        "当前目录下可读的文件有：notes.txt、tools.py、executors.py、README.md、config.py",
    ),
    ("④ 看起来可重试", "读取服务暂时不可用，请稍后重试"),
]


def main() -> None:
    # ---- 第一轮：只跑一次，四个变体共用这条 assistant 回复 ----
    first = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": QUESTION}],
        tools=TOOLS,
        extra_body={"thinking": {"type": "enabled"}},
    )
    msg = first.choices[0].message
    if not msg.tool_calls:
        print(f"第一轮模型没调工具，探针没法继续（finish_reason={first.choices[0].finish_reason}）")
        return

    calls = msg.tool_calls
    print(f"第一轮：调了 {len(calls)} 个工具 —— " + "、".join(c.function.arguments for c in calls))
    print(f"         finish_reason={first.choices[0].finish_reason}\n")

    # ---- 第二轮：四个变体，只有 tool 消息的 content 不同 ----
    for label, error_text in ERROR_VARIANTS:
        messages = [
            {"role": "user", "content": QUESTION},
            msg,  # 同一个 assistant 回复，原样复用
        ]
        # 必须**每个** tool_call 各回一条 —— 少回一条就是上面那个 400。
        for c in calls:
            messages.append({"role": "tool", "tool_call_id": c.id, "content": error_text})
        second = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            extra_body={"thinking": {"type": "enabled"}},
        )
        m = second.choices[0].message
        fr = second.choices[0].finish_reason

        if m.tool_calls:
            retried = "、".join(f"{c.function.name}({c.function.arguments})" for c in m.tool_calls)
            print(f"{label}: finish_reason={fr}  → 重试了：{retried}")
        else:
            print(f"{label}: finish_reason={fr}  → 放弃，文本回答：{(m.content or '')[:70]!r}")


if __name__ == "__main__":
    main()
