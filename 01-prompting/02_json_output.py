"""01-2 结构化输出（response_format）

目标：让模型的输出变成**程序能直接用的 dict**，而不是「看起来像 JSON 的字符串」。
     这是从「聊天玩具」到「能写进代码的组件」的关键一步。

验收标准（详见 ./README.md）：
  [ ] 用 response_format={"type": "json_object"}，而不是只在提示词里求它
  [ ] 提示词里必须出现 "json" 这个词，并且给出期望格式的**例子**
  [ ] 拿到的是**字符串**，要自己 json.loads()
  [ ] schema 写复杂一点（嵌套对象 + 数组 + 枚举）也稳
  [ ] 撞一次「JSON 模式偶尔返回空 content」的已知问题

本次实验只关心三件事：
  ① 不传 response_format 会怎样 —— 同一个提示词跑两次做对照
  ② 嵌套 schema 稳不稳
  ③ 「JSON 模式偶发空 content」能不能撞上

--- 关键 API ---

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "……要求返回 json……"}],
        response_format={"type": "json_object"},   # ← 约束在这里
    )

    raw  = response.choices[0].message.content    # ← 是 str，不是 dict！
    data = json.loads(raw)                        # ← 这一步省不掉

  跟 Claude 的区别：Claude 走 **tool use** 做结构化输出时，参数是**已经解析好的对象**
  （`tool_use.input` 直接就是 dict）。DeepSeek 只保证「content 是一段合法 JSON 字符串」，
  解析是你自己的事。

  注意别搞反因果：不是「Claude 的模型能返回 dict，DeepSeek 的不能」——
  模型只会吐 token，吐出来的天然就是文本。区别在于 Claude 那条路把结果放进了
  一个**结构化字段**里，而 response_format 只是**约束它吐的文本**长得合法。
  （顺带：DeepSeek 的 tool_calls 参数**又是字符串**，见根 README 约定 5。）

--- 实测记录（2026-09-27，openai 3.19.2 + DeepSeek）---

  下面四条是真跑出来的，不是从文档抄的：

  1. content 的类型确实是 str，json.loads() 之后才是 dict。

  2. **提示词里不出现 "json" 这个词 → 请求直接 400**：

         Prompt must contain the word 'json' in some form
         to use 'response_format' of type 'json_object'.

     这个 400 是**服务端在模型启动前**做的参数校验，模型压根没被调用 ——
     本质是个 if 判断，检查 messages 里有没有 "json" 子串。
     所以不是「一直输出空白直到撞上限」，而是一撞就报，很好定位。

  3. **思考模式能和 json_object 共存**。实测 reasoning_content 有一大段，
     content 是干净的 JSON，互不污染。这点比手动 CoT 省事（见 04）。

  4. **模型偶尔会把 response_format 的值当字段回显出来**。
     实测出现过 content 里莫名多一个 "type": "json_object" 字段。
     所以校验时按「我需要的字段在不在」来判，别假设输出只有你列的那些字段。

--- 坑 ---

  · **max_tokens 别设太小**。JSON 被从中间截断，finish_reason 会变成 length，
    那串东西再也 json.loads() 不出来。
  · **「空 content」和「格式错」是两回事**（05 会细处理）：
      - 空 content：JSON 模式下偶尔出现，官方承认的已知问题 → 原样重试
      - 格式错：吐了个语法坏掉的 JSON → 要把错误信息回传给模型让它修
"""

import json

from config import MODEL, client

# 提示词硬性要求两条，缺第一条连请求都发不出去（400）：
#   ① 出现 "json" 这个词
#   ② 给出期望格式的**例子** —— 光说「返回 json」模型不知道你要哪些字段
# 对照实验用的这个提示词，值故意写成**中文占位符**（姓名 / 年龄(整数) / 城市），
# 看着像"模板"而不是"输出样例"。实测这种写法会让模型先解释、再套 ```json 代码块。
# 换成填好的具体值（"张三" / 30 / "北京"）就不会 —— 这个差别就是本次要看的。
PERSON_PROMPT = """从下面这句话里抽取人物信息，用 json 输出。
schema: {"name": 姓名, "age": 年龄(整数), "city": 城市}

句子：李四是一个居住在上海的四十岁男人
"""

NESTED_PROMPT = """
你要用json的格式回答我的问题
schema:
{
  "company": 公司名,
  "candidates": [
    {"name": "张三", "years": 5, "tags": ["python", "sql"]},
    {"name": "李四", "years": 3, "tags": ["java", "k8s"]}
  ]
}
王五在美团工作八年，主要用python写opencv
"""


def ask_json(prompt: str, use_response_format: bool = True) -> str:
    """发一次请求，返回 content 的**原始字符串**（不解析）。

    use_response_format=False 时**不传** response_format，其余字段一模一样 ——
    对照组和实验组只差下面那个 if，差异才归因得清。
    """
    request = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": "high",
        "extra_body": {"thinking": {"type": "enabled"}},
    }
    if use_response_format:
        request["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**request)
    return response.choices[0].message.content


def compare_with_and_without() -> None:
    """同一个提示词，带 / 不带 response_format 各跑一次，并排对照。

    看三样：content 的**类型**、**原文**、**json.loads 成不成**。
    原文必须用 repr() 打，否则围栏和换行会被吃掉，等于没看。
    """
    for label, use_format in (("带 response_format", True), ("不带 response_format", False)):
        raw = ask_json(PERSON_PROMPT, use_response_format=use_format)

        print(f"\n--- {label} ---")
        print("类型 :", type(raw).__name__)
        print("原文 :", repr(raw))
        try:
            json.loads(raw)
            print("json.loads → 成功")
        except json.JSONDecodeError as e:
            print(f"json.loads → 失败：{e}")


def ask_nested() -> None:
    """嵌套 schema：能解析只算及格，还要逐条查字段内容和类型。"""
    raw = ask_json(NESTED_PROMPT)
    data = json.loads(raw)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    candidates = data.get("candidates")
    print("candidates 是 list 吗 :", isinstance(candidates, list))

    for candidate in candidates or []:
        # !r 会带引号：5 打成 5，而 "5" 打成 '5' —— 一眼看出类型对不对
        print(
            f"  {candidate.get('name')}"
            f"  years={candidate.get('years')!r}"
            f"  tags={candidate.get('tags')!r}"
        )


def hunt_empty_content(times: int = 30) -> None:
    """跑 times 次，统计空 content 出现几次。"""
    empty_count = 0
    for i in range(times):
        raw = ask_json('返回一个 json：{"ok": true}')
        if not raw:  # None 和 "" 都是假值，一个判断盖住两种
            empty_count += 1
            print(f"  第 {i + 1} 次撞上空 content")

    print(f"跑了 {times} 次，空 content 出现 {empty_count} 次，比例 {empty_count / times:.1%}")


if __name__ == "__main__":
    print("== 对照：带 / 不带 response_format ==")
    compare_with_and_without()

    print("\n== 嵌套 schema ==")
    ask_nested()

    print("\n== 猎空 content ==")
    hunt_empty_content(times=30)
