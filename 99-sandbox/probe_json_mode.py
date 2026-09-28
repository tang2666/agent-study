"""临时探针：实测 response_format={"type": "json_object"} 在 DeepSeek 上的行为。

要回答四个问题：
  1. content 到底是字符串还是 dict？
  2. 提示词里不出现 "json" 这个词会怎样？
  3. 思考模式开着的时候，能不能和 json_object 共存？
  4. 复杂 schema（嵌套 + 数组 + 枚举）稳不稳？
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402


def call(prompt, *, json_mode=True, thinking=True, max_tokens=None):
    kwargs = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": "high",
        "extra_body": {"thinking": {"type": "enabled" if thinking else "disabled"}},
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return client.chat.completions.create(**kwargs)


print("=" * 70)
print("① 提示词里带 json + 思考开着")
print("=" * 70)
r = call('返回一个 json，描述一个人：name=张三, age=30, skills=["python","sql"]')
m = r.choices[0].message
print("content 的类型 :", type(m.content).__name__)
print("content 原文   :", repr(m.content))
print("reasoning 有吗 :", m.reasoning_content is not None,
      f"(长度 {len(m.reasoning_content or '')})")
print("finish_reason  :", r.choices[0].finish_reason)
print("json.loads() 后:", json.loads(m.content))

print()
print("=" * 70)
print("② 提示词里【不】出现 json 这个词")
print("=" * 70)
try:
    r = call("描述一个人：name=张三, age=30, skills=[python, sql]", max_tokens=200)
    m = r.choices[0].message
    print("content 原文   :", repr((m.content or "")[:200]))
    print("finish_reason  :", r.choices[0].finish_reason)
except Exception as e:  # noqa: BLE001 - 探针就是要看抛什么
    print(f"直接抛异常！{type(e).__name__}")
    print(f"  {e}")

print()
print("=" * 70)
print("③ 思考模式【关掉】+ json")
print("=" * 70)
r = call('返回一个 json，描述一个人：name=李四, age=25', thinking=False)
m = r.choices[0].message
print("content 原文   :", repr(m.content))
print("hasattr reasoning_content :", hasattr(m, "reasoning_content"))
print("getattr 兜底   :", getattr(m, "reasoning_content", "<属性不存在>"))
print("message 的字段 :", sorted(m.model_fields_set))

print()
print("=" * 70)
print("④ 复杂 schema：嵌套对象 + 数组 + 枚举")
print("=" * 70)
prompt = """从下面这段文字里抽取信息，返回 json。schema 如下：
{
  "company": "公司名",
  "year": 年份(整数),
  "level": "初级" | "中级" | "高级",
  "candidates": [
     {"name": "姓名", "years": 工作年数(整数), "tags": ["技能", ...]}
  ]
}

文字：字节跳动 2024 年招聘，级别是高级。候选人两位：
张三是 5 年经验的 python 工程师，会 sql；李四 3 年经验，会 java 和 k8s。
"""
r = call(prompt)
m = r.choices[0].message
print("content 原文   :", repr(m.content)[:400])
print()
parsed = json.loads(m.content)
print("解析后         :", json.dumps(parsed, ensure_ascii=False, indent=2))
print("level 是否合法 :", parsed.get("level") in ("初级", "中级", "高级"))
print("candidates 是列表吗:", isinstance(parsed.get("candidates"), list))
