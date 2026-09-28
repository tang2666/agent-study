"""临时探针：把整个 chunk 时间线打出来，重点看"思考 → 正文"的切换点。

验三件事：
  1. chunk 总数、每个 chunk 属于哪个阶段
  2. 切换点在第几个 chunk
  3. 有没有哪个 chunk 两个字段同时有值
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用一句话解释什么是 token。"}],
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
    stream=True,
)

chunks = list(stream)
deltas = [c.choices[0].delta for c in chunks]

both = [i for i, d in enumerate(deltas) if d.reasoning_content and d.content]
reasoning_idx = [i for i, d in enumerate(deltas) if d.reasoning_content]
content_idx = [i for i, d in enumerate(deltas) if d.content]

print(f"chunk 总数：{len(chunks)}")
print(
    f"reasoning_content 有值的：第 {reasoning_idx[0]} ~ {reasoning_idx[-1]} 个，"
    f"共 {len(reasoning_idx)} 个"
)
print(f"content 有值的：      第 {content_idx[0]} ~ {content_idx[-1]} 个，共 {len(content_idx)} 个")
print(f"两个字段同时有值的：  {both if both else '没有，一个都没有'}")

print("\n=== 切换点前后各 3 个 chunk ===")
lo = max(0, content_idx[0] - 3)
hi = min(len(deltas), content_idx[0] + 3)
for i in range(lo, hi):
    d = deltas[i]
    mark = "  <-- 正文从这里开始" if i == content_idx[0] else ""
    print(
        f"[{i:3d}] "
        f"reasoning={d.reasoning_content!r:20} "
        f"content={d.content!r:14} "
        f"finish={chunks[i].choices[0].finish_reason}{mark}"
    )

print("\n=== 最后 2 个 chunk ===")
for i in range(len(deltas) - 2, len(deltas)):
    d = deltas[i]
    print(
        f"[{i:3d}] "
        f"reasoning={d.reasoning_content!r:20} "
        f"content={d.content!r:14} "
        f"finish={chunks[i].choices[0].finish_reason} "
        f"usage={'有' if chunks[i].usage else 'None'}"
    )
