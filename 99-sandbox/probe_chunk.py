"""临时探针：把流式 chunk 的真实结构打出来。看完就能删。"""

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
print(f"总共收到 {len(chunks)} 个 chunk\n")

print("=== 第 1 个 chunk 的完整 JSON ===")
print(chunks[0].model_dump_json(indent=2))

print("\n=== 第 2 个 chunk 的完整 JSON ===")
print(chunks[1].model_dump_json(indent=2))

print("\n=== 倒数第 2 个 chunk 的完整 JSON ===")
print(chunks[-2].model_dump_json(indent=2))

print("\n=== 最后 1 个 chunk 的完整 JSON ===")
print(chunks[-1].model_dump_json(indent=2))

print("\n=== 每个 chunk 的 delta 长什么样（前 10 个）===")
for i, c in enumerate(chunks[:10]):
    d = c.choices[0].delta
    print(f"[{i}] reasoning_content={d.reasoning_content!r}  content={d.content!r}")
