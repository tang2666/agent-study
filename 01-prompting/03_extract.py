"""01-3 真实提取任务

目标：设计一份能被 10 段真实脏文本扛住的 schema。

分工（这一节故意反过来了）：
  · 10 段文本**已经给你了**（见下方 SAMPLE_TEXTS）—— 是我写的，故意做脏的
  · **schema 由你设计** —— 这是本节唯一的考点
  · 验收由我来做

验收标准（详见 ./README.md）：
  [ ] 至少 5 个字段，其中含一个**嵌套结构**
  [ ] 10 段文本全部成功解析，没有一次需要人工修
  [ ] 对「文本里根本没这个信息」的情况有明确处理

--- 关键 API ---

  跟 02 完全一样，没有新东西：

      response = client.chat.completions.create(
          model=MODEL,
          messages=[{"role": "user", "content": 提示词}],
          response_format={"type": "json_object"},
      )
      data = json.loads(response.choices[0].message.content)

  这一节考的是**提示词和 schema 怎么设计**，不是 API 怎么调。

--- 三个设计决定，先想清楚再动手 ---

  这三个决定你只要有一个没想清楚，10 段里一定有几段会翻车。
  而它们**光看一段干净文本是发现不了的** —— 这就是为什么需要一批脏文本。

  1. **缺信息怎么办？** 两条路，各有利弊：

       · 字段填 null —— 诚实，但下游每次都要判空
       · 给默认值或不输出 —— 下游省事，但你分不清「真没有」和「模型漏了」

     推荐 null，并且必须在提示词里**明写**「找不到就填 null，不要猜」。
     不写这句，模型一定会编一个给你 —— 它天生倾向于把表格填满。

  2. **枚举值要封闭**。比如「学历」只允许 本科/硕士/博士/其他 四个值。
     只写「学历」两个字，模型会自由发挥出「本科在读」「985」「统招本科」……
     下游没法用。把取值写死在提示词里，并且**在代码里也校验一遍**。

  3. **数量可变的数组**，比如「技能列表」「工作经历列表」。想清楚空数组 `[]`
     和 null 的区别：
         []   = 文本里提到了这个人、也提到了这一项，但内容是空的
         null = 文本里压根没提这一项
     别把两者混成一个。

--- 那 10 段文本怎么用 ---

  它们是故意做脏的：有信息齐全的、有缺东西的、有口语到几乎没法抽的、
  有提到别人的、有格式乱的、有自相矛盾的。

  **哪段是哪种，我不标。** 你得自己从文本里读出来 —— 这本身就是
  「该考虑哪些边界」的一部分。（验收时我会告诉你每段在测什么。）

  建议的节奏：**别一次把 schema 定死**。先设计一版 → 跑这 10 段 →
  被哪段打脸就改 schema/提示词 → 再跑。真实工作就是这个循环，
  schema 不是设计出来再验证的，是被脏数据打出来的。
"""

import json

from config import MODEL, client

# 自己挑领域，自己设计字段。至少 5 个，其中一个是嵌套（比如工作经历是对象数组）。
#
# 动手前先把上面「三个设计决定」想清楚 —— 那才是这一节的考点。
# 提示：照着 SAMPLE_TEXTS 里真实出现的信息设计，别设计一堆文本里根本没有的字段，
# 那样你测不出 null 的处理。
# 纯结构：字段名、嵌套、类型、每个字段自己的取值范围。
# 只有这部分是「能被别的程序复用」的 —— 存文件、生成文档、喂给正式 schema API 都行。
EXTRACT_SCHEMA = """
{
  "name": "候选人姓名",
  "sex": "性别，只能取 男 或 女",
  "education": "最高学历，只能取 博士 / 硕士 / 本科 / 大专 / 其他（博士后记作 博士）",
  "skills": ["这个人掌握的技能"],
  "experiences": [
    {
      "startTime": "开始时间",
      "endTime": "结束时间",
      "company": "单位名称",
      "job": "职位"
    }
  ],
  "expected_salary": "期望薪资",
  "expected_position": "期望职位"
}
"""

# 跨字段的规则：模型怎么处理「缺」和「边界」。这些是给模型的指令，
# 不是结构的一部分 —— 拆出来是为了让上面那个常量保持纯净。
EXTRACT_RULES = """抽取规则：
1. 文本里找不到的信息一律填 null，严禁猜测或编造。
   尤其是性别：文本没写就填 null，不要根据姓名或昵称推测。
2. sex 和 education 只能取 schema 里列出的值，不要自创（如"985""统招本科"）。
3. skills 和 experiences 是数组，null 和 [] 含义不同，别混成一个：
     null = 整段文本压根没提这件事
     []   = 文本提到了，但明确说没有（如"应届生，暂无工作经验"）
4. 学历、技能属于「人」本身，不要塞进 experiences 的某一条里。
"""

SYSTEM_PROMPT = f"请将下列文本按照我给的 schema 总结成一份 json\n{EXTRACT_SCHEMA}\n{EXTRACT_RULES}"

# 代码侧的封闭枚举 —— 光写在提示词里不算数，模型偶尔会自创取值
SEX_VALUES = {"男", "女"}
EDUCATION_VALUES = {"博士", "硕士", "本科", "大专", "其他"}

# 10 段候选人文本，故意做脏。别改它们 —— 改了就不算同一场考试了。
SAMPLE_TEXTS = [
    (
        "【候选人】张伟，男，1995年3月生。2017年本科毕业于华中科技大学计算机专业。"
        "2017年7月至2020年6月在武汉一家创业公司做后端开发，"
        "2020年8月至今在字节跳动任高级后端工程师。熟悉 Java、Python、MySQL、Redis。"
        "期望薪资 35K-45K。"
    ),
    "王芳，女。2019 年到 2022 年在杭州一家电商公司做测试。目前待业，想找远程的岗位。",
    (
        "老王，干了五年后端了吧，python 挺熟的。之前在那个……呃，一个做 SaaS 的小厂，"
        "后来跳去大厂了。本科，好像是计算机的。"
    ),
    (
        "昨天面了李明，他之前在腾讯做前端，五年经验。我们组的赵敏负责记录，"
        "她觉得李明沟通不错。推荐人写的是孙鹏，是他前同事。"
    ),
    "陈静，博士后。目前是 P8 级架构师，在阿里工作 6 年。",
    "吴磊，男，26 岁，本科，应届毕业生。熟悉 C++、Go 和 Docker，暂无工作经验。",
    "李娜，2016 年本科毕业，有 3 年工作经验，目前在杭州做数据分析。",
    "郑凯 男 92年生 大专 2014.3-2018.9 做运维 2019.1-现在 做 SRE 深圳 会 shell python",
    "刘洋，女，硕士。",
    (
        "黄建国，1978 年生，男，博士。2005 年博士毕业于中科院自动化所。"
        "2005-2010 年在微软亚洲研究院任研究员，2010-2015 年任百度高级技术经理，"
        "2015 年至今在商汤科技任技术副总裁。精通机器学习、计算机视觉。"
        "期望职位：CTO 或技术合伙人。"
    ),
]



def build_prompt(text: str) -> str:
    """把「schema 说明 + 输出例子」和「待抽取的文本」拼成一个提示词。

    注意 `text` 是**待抽取的那段输入文本**（SAMPLE_TEXTS 里的某一段），
    不是 schema。schema 是模块顶部的 EXTRACT_SCHEMA —— 你设计好的常量，
    在这里直接引用就行。

    顺序也有讲究：schema / 规则 / 例子放前面（10 次调用都一样），
    text 放最后（每次变）—— 这样前缀能命中缓存（见 01 章）。

    记住 02 的实测结论：提示词里**必须**出现 "json" 这个词，否则直接 400。
    也别在三个地方各写一份 schema —— 说明和例子都来自 EXTRACT_SCHEMA，改一处就够。
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},  # 角色 / 规则 / 约束
            {"role": "user", "content": text},  # 本次要处理的内容
        ],
        response_format={"type":"json_object"},
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    return response.choices[0].message.content


def validate(data: dict) -> list[str]:
    """代码侧的校验：枚举有没有跑偏、数组字段类型对不对。

    返回问题列表，空列表 = 通过。提示词里的约束是「请求」，
    这里才是「强制」—— 模型偶尔会自创取值（"985""统招本科"）。
    """
    problems = []
    if data.get("sex") is not None and data["sex"] not in SEX_VALUES:
        problems.append(f"sex={data['sex']!r} 不在 {SEX_VALUES}")
    if data.get("education") is not None and data["education"] not in EDUCATION_VALUES:
        problems.append(f"education={data['education']!r} 不在 {EDUCATION_VALUES}")
    for field in ("skills", "experiences"):
        value = data.get(field)
        if value is not None and not isinstance(value, list):
            problems.append(f"{field} 应该是数组或 null，实际是 {type(value).__name__}")
    return problems


def extract(text: str) -> dict | None:
    """抽取一段文本。成功返回 dict，失败返回 None。"""
    # JSON 模式偶发空 content（见 02 章的已知问题）——先挡掉，
    # 否则 json.loads(None) 抛的是 TypeError，下面的 except 抓不到
    if not text:
        print("  空 content")
        return None

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"  解析失败：{type(e).__name__}: {e}")
        print(f"  原始 content：{text!r}")
        return None

    problems = validate(data)
    if problems:
        print(f"  校验失败：{problems}")
        print(f"  原始 content：{text!r}")
        return None
    return data


def run_all() -> None:
    """把 SAMPLE_TEXTS 全跑一遍，统计成功率。

    一段失败时，除了异常还要把**原始 content** 打出来 ——
    你需要看到模型到底吐了什么，光看 traceback 不够。
    """
    fail = 0
    for i, text in enumerate(SAMPLE_TEXTS, start=1):
        print(f"\n--- 第 {i} 段 ---")
        ans = extract(build_prompt(text))
        if ans is None:
            fail += 1
        else:
            print(ans)

    total = len(SAMPLE_TEXTS)
    print(f"\n成功 {total - fail}/{total}，失败 {fail}")

if __name__ == "__main__":
    run_all()
