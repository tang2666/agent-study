"""临时探针：同一个提示词，加不加 response_format，content 到底差在哪？

要回答：既然 content 永远是 str，response_format 到底改了什么？
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

# 故意挑一个「天然会引来寒暄」的提示词：模型很可能会说「好的，这是抽取结果：」
# 然后再给 json。这种前缀对人无所谓，对 json.loads() 是致命的。
PROMPT = """从下面这句话里抽取信息，用 json 表示。
schema: {"name": "姓名", "age": 年龄(整数), "skills": ["技能"]}

句子：李四今年 28 岁，是后端工程师，会 python 和 go。
"""


def run(label: str, use_response_format: bool) -> None:
    print("=" * 70)
    print(label)
    print("=" * 70)

    for i in range(3):
        kwargs = {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "extra_body": {"thinking": {"type": "disabled"}},  # 关思考，省点钱也快点
        }
        if use_response_format:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        raw = choice.message.content

        print(f"\n--- 第 {i + 1} 次 (finish_reason={choice.finish_reason}) ---")
        print("raw 类型 :", type(raw).__name__)
        print("raw 原文 :", repr(raw)[:300])

        try:
            json.loads(raw)
            print("json.loads → 成功")
        except Exception as e:  # noqa: BLE001 - 探针就是要看它炸成什么样
            print(f"json.loads → 失败：{type(e).__name__}: {e}")


run("① 不加 response_format", use_response_format=False)
run("② 加了 response_format", use_response_format=True)
