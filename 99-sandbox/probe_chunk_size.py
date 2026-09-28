"""临时探针：chunk 的大小和 token 数是一回事吗？"""

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
usage = None
texts = []
for c in chunks:
    if c.usage:
        usage = c.usage
    d = c.choices[0].delta
    t = (d.reasoning_content or "") + (d.content or "")
    texts.append(t)

nonempty = [t for t in texts if t]
print(f"chunk 总数：{len(chunks)}")
print(f"带内容的 chunk：{len(nonempty)}")
print(f"completion_tokens（服务端报的）：{usage.completion_tokens}")

print("\n=== 长度分布（字符数 → 有几个 chunk）===")
from collections import Counter  # noqa: E402

for n, cnt in sorted(Counter(len(t) for t in nonempty).items()):
    print(f"  {n} 字符：{cnt} 个 chunk")

print("\n=== 最长的 8 个 chunk ===")
for t in sorted(nonempty, key=len, reverse=True)[:8]:
    print(f"  {len(t):2d} 字符  {t!r}")
