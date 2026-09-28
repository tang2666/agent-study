"""临时探针：不带 response_format 时，「套不套 ```json 围栏」到底由什么决定？

起因：我在探针里（thinking 关闭）得到「中文占位符 → 0/10 成功」，
     但用户在自己的练习文件里（thinking 打开）同样的提示词却是干净 JSON。
     说明还有一个变量没控制住。

候选变量：
  · 思考模式 开 / 关
  · 提示词里 schema 的值是「中文占位符」还是「填好的具体值」

做法：两个提示词 × 思考开/关，各跑 6 次，都不传 response_format，数成功率。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-hello-llm"))

from config import MODEL, client  # noqa: E402

RUNS = 6

# 用户练习文件里的写法：值用中文占位符，看着像"模板"
PROMPT_PLACEHOLDER = """从下面这句话里抽取人物信息，用 json 输出。
schema: {"name": 姓名, "age": 年龄(整数), "city": 城市}

句子：李四是一个居住在上海的四十岁男人
"""

# 只把值换成填好的具体例子，其余一字不动
PROMPT_CONCRETE = """从下面这句话里抽取人物信息，用 json 输出。
schema: {"name": "张三", "age": 30, "city": "北京"}

句子：李四是一个居住在上海的四十岁男人
"""


def ask(prompt: str, thinking: bool) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled" if thinking else "disabled"}},
    )
    return response.choices[0].message.content


def measure(label: str, prompt: str, thinking: bool) -> None:
    ok_count = 0
    first_failure = None

    for _ in range(RUNS):
        raw = ask(prompt, thinking)
        try:
            json.loads(raw)
            ok_count += 1
        except json.JSONDecodeError:
            if first_failure is None:
                first_failure = raw

    print(f"{label:38s} 成功 {ok_count}/{RUNS}", end="")
    if first_failure is not None:
        print(f"   例：{first_failure!r}")
    else:
        print()


# 只把标签从 "schema:" 换成 "输出示例："，其余一字不动
PROMPT_OUTPUT_EXAMPLE_PLACEHOLDER = PROMPT_PLACEHOLDER.replace("schema:", "输出示例：")
PROMPT_OUTPUT_EXAMPLE_CONCRETE = PROMPT_CONCRETE.replace("schema:", "输出示例：")


measure("schema:   + 占位符 + 思考开", PROMPT_PLACEHOLDER, thinking=True)
measure("schema:   + 占位符 + 思考关", PROMPT_PLACEHOLDER, thinking=False)
measure("schema:   + 具体值 + 思考开", PROMPT_CONCRETE, thinking=True)
measure("schema:   + 具体值 + 思考关", PROMPT_CONCRETE, thinking=False)
measure("输出示例： + 占位符 + 思考关", PROMPT_OUTPUT_EXAMPLE_PLACEHOLDER, thinking=False)
measure("输出示例： + 具体值 + 思考关", PROMPT_OUTPUT_EXAMPLE_CONCRETE, thinking=False)
