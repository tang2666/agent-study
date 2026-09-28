"""临时探针：不传 response_format 时，「输出能不能 json.loads」到底稳不稳？

背景：用户实测发现「不带参数也返回了标准 JSON」，所以怀疑这个参数没用。
假设：那次成功是因为**提示词写得好**（例子内联，引着模型从 { 开始），
      换个写法就会崩 —— 也就是说"不带参数也成功"是碰巧，不是保证。

做法：两种提示词写法，各跑 10 次，都不传 response_format，数成功率。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

RUNS = 10

# A：例子内联在句子里（用户那版的写法）
PROMPT_INLINE = """我需要你以json的格式返回给我告诉你的信息
类似于{"name": "张三", "age": 30, "city": "北京"}

李四是一个居住在上海的四十岁男人
"""

# B：例子单独放一段（我原来探针那版的写法）
PROMPT_BLOCK = """从下面这句话里抽取人物信息，返回一个 json 对象。

格式示例：
{"name": "张三", "age": 30, "city": "北京"}

李四是一个居住在上海的四十岁男人
"""


def ask_without_format(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}},  # 关思考，省点钱
    )
    return response.choices[0].message.content


def measure(label: str, prompt: str) -> None:
    ok_count = 0
    first_failure = None

    for _ in range(RUNS):
        raw = ask_without_format(prompt)
        try:
            json.loads(raw)
            ok_count += 1
        except json.JSONDecodeError:
            if first_failure is None:
                first_failure = raw

    print(f"\n{label}")
    print(f"  json.loads 成功 {ok_count}/{RUNS}")
    if first_failure is not None:
        print(f"  一次失败的原文：{first_failure!r}")


# C：早先那个「3/3 全崩」的原文案 —— 值是中文占位符，看着像"模板"
PROMPT_PLACEHOLDER = """从下面这句话里抽取信息，用 json 表示。
schema: {"name": "姓名", "age": 年龄(整数), "skills": ["技能"]}

句子：李四今年 28 岁，是后端工程师，会 python 和 go。
"""

# D：跟 C 只差一处 —— 值换成填好的具体例子
PROMPT_CONCRETE = """从下面这句话里抽取信息，用 json 表示。
输出示例：{"name": "张三", "age": 30, "skills": ["python", "sql"]}

句子：李四今年 28 岁，是后端工程师，会 python 和 go。
"""


measure("A 例子内联在句子里", PROMPT_INLINE)
measure("B 例子单独放一段", PROMPT_BLOCK)
measure("C 中文占位符 + schema:", PROMPT_PLACEHOLDER)
measure("D 具体值 + 输出示例：", PROMPT_CONCRETE)
