"""01-4 思维链（CoT）：三种问法

目标：分清**两种 CoT**，别糊成一团 —— 这是这一章最容易混的概念。

      A. 手动 CoT    在 prompt 里求「先分步推理，再给结论」。推理过程写在 content 里，
                     和结论混在同一段文本里，你得自己想办法把结论抠出来。
      B. 直接问答案  不要求推理，一步到位。
      C. 原生思考模式 **默认就开着**，什么都不传它就在想（见实测记录 4）。
                     推理过程在 reasoning_content 里，和 content **天然分开**，不用你抠。

验收标准（详见 ./README.md）：
  [ ] 跑 A vs B，能观察到 A 更准（如果一样准，换个更难的问题）
  [ ] 跑 C，对比「开思考 / 关思考」两种输出的差异
  [ ] 关键对比：A 的推理在哪、C 的推理在哪？原生思考比手动 CoT 多解决了什么？
  [ ] 思考：下游只要结论时，A 和 C 各自怎么拿到干净结果？哪个省事？为什么？

--- 关键 API ---

  三种问法的差别只有两处：prompt 怎么写、extra_body 怎么传。

      # A 手动 CoT：靠 prompt 求它，代码上跟 B 一模一样
      messages=[{"role": "user", "content": "请一步步推理，最后单独一行写「答案：…」\n" + 题}]

      # B 直接问：什么都不加
      messages=[{"role": "user", "content": 题}]

      # C 原生思考：prompt 也可以什么都不加，思考由参数控制
      client.chat.completions.create(
          model=MODEL,
          messages=[{"role": "user", "content": 题}],
          reasoning_effort="high",                            # 开了才有 reasoning_content
          extra_body={"thinking": {"type": "enabled"}},       # "disabled" 就是关
      )

--- 实测记录（2026-09-27，openai 3.19.2 + DeepSeek）---

  1. **关思考之后，`reasoning_content` 是「属性不存在」，不是 None。**

         开：message.reasoning_content  → 一段 str
         关：message.reasoning_content  → AttributeError: 'Choice' object has no attribute ...

     所以别写 `if message.reasoning_content is None`，那行代码在关思考时会直接抛。
     要安全取值就用 `getattr(message, "reasoning_content", None)`。

     （注意这跟**流式**不一样：流式的每个 chunk 里 reasoning_content 是显式的 null。）

  2. **手动 CoT 的坑：结论和推理在同一条 content 里**。模型不一定乖乖
     「最后一行写答案」，它可能把答案写在中间，或者边推理边给好几个备选。
     你要么在 prompt 里把格式钉死，要么写正则在 content 里抠 —— 这就是 C 省事的地方。

  3. **原生思考不一定比手动 CoT 便宜**。思考模式会真的生成一大段 token，
     都算 completion 的钱。但它的好处是干净的字段分离。

  4. **思考模式默认就是开的 —— 什么都不传它就在想。**

         什么都不传                    → reasoning_content 有内容（实测 237 字）
         只传 reasoning_effort="high"  → 同上（effort 只是调档位，它不是开关）
         thinking: disabled            → 属性不存在，就是记录 1 里"关思考"那种状态

     所以 A / B 两组要显式写 `thinking: disabled`：不是去"打开思考"，
     而是**把它关掉**。不关的话你测的就不是"手动 CoT"，
     而是"手动 CoT + 原生思考"两件事混在一起，对照就废了。

  5. **「不要求推理」挡不住模型自己写推理。** 只传一句"直接给答案"，
     它面对数学题照样把过程全写进 content —— 所以 B 必须**明令禁止**
     （"只输出最终答案，不要步骤"），否则 A 和 B 都在写步骤，对照白做。

--- 坑 ---

  · **思考模式下 `temperature` / `presence_penalty` / `frequency_penalty` 静默失效**
    （根 README 约定 2）。想「调低温度让推理稳一点」在这个模型上是假动作。
  · **思考模式下 `content` 理论上可能为空**（推理有了但没吐正文）。
    这跟 02 里那个「JSON 模式偶发空 content」是两码事，别混。
  · 挑题别挑太简单的。像「1+1」三种问法全对，你什么都观察不到；
    挑个需要绕两步的（鸡兔同笼 / 逻辑推断 / 稍微绕的应用题）。
"""
from config import MODEL, client

# 挑题：光「多几步算术」不够，得有个**凭直觉会踩的陷阱**，才看得出区别。
#   陷阱：把两个数直接相减  →  50 - 20 - 15 = 15（错，漏了重合的 5 人）
#   正解：至少会一样 = 20 + 15 - 5 = 30，两样都不会 = 50 - 30 = 20
# 一次前向的直觉容易踩 15；把中间步骤写出来，才不容易漏掉重合的那 5 人。
QUESTION = (
    "某公司有 50 名员工。其中 20 人会游泳，15 人会骑自行车，5 人两样都会。"
    "问：两样都不会的有多少人？"
)

# A 的 prompt：关键是**把输出格式钉死**，否则结论混在推理里抠不出来。
MANUAL_COT_PROMPT = "先一步步推理，写出每一步的计算。最后单独一行写「答案：…」"

# B 的 prompt：光"不要求推理"挡不住模型（见实测记录 5），得**明令禁止**。
DIRECT_PROMPT = "只输出最终答案，不要写任何推理过程、步骤、解释或多余文字。"


def read_reply(response) -> tuple[str, str]:
    """把一条回复拆成 (reasoning, content)。

    关思考时 message 上**根本没有** reasoning_content 属性，用 getattr 兜住
    （docstring 实测记录 1），取不到就给空串，别让它抛 AttributeError。
    """
    msg = response.choices[0].message
    return getattr(msg, "reasoning_content", None) or "", msg.content or ""


def ask_direct(question: str) -> tuple[str, str]:
    """B：明令禁止写步骤，答案得一次蹦出来。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": DIRECT_PROMPT},
            {"role": "user", "content": question},
        ],
        extra_body={"thinking": {"type": "disabled"}},  # 思考也不开，B 才是"纯一次前向"
    )
    return read_reply(response)


def ask_manual_cot(question: str) -> tuple[str, str]:
    """A：在 prompt 里求 CoT，推理和结论都落在 content 里。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": MANUAL_COT_PROMPT},
            {"role": "user", "content": question},
        ],
        extra_body={"thinking": {"type": "disabled"}},  # 同上，别让原生思考混进来
    )
    return read_reply(response)


def ask_native_thinking(question: str, thinking: bool = True) -> tuple[str, str]:
    """C：原生思考，推理进 reasoning_content，content 保持干净。

    thinking=False = 同一句话问它、但不给草稿纸 —— 正好做验收里的
    「开思考 / 关思考」对照，两者只差这个开关。
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled" if thinking else "disabled"}},
    )
    return read_reply(response)


def show(label: str, reply: tuple[str, str]) -> None:
    """把一条回复的两个字段分开打出来。"""
    reasoning, content = reply
    print(f"\n{'=' * 56}")
    print(label)
    print("=" * 56)
    print(f"[reasoning_content] {len(reasoning)} 字")
    print(reasoning if reasoning else "（空 —— 这条没开思考）")
    print(f"[content] {len(content)} 字")
    print(content)


def compare() -> None:
    """把 A / B / C 三种输出并排打出来。

    重点看两件事：
      1. A 和 B 谁答对 —— B 被禁止写步骤，答案得一次蹦出来
      2. A 的推理在 content 里、C 的推理在 reasoning_content 里 —— 字段分开了
    """
    print(f"题目：{QUESTION}")
    show("A 手动 CoT —— 求它写步骤", ask_manual_cot(QUESTION))
    show("B 直接问 —— 禁止写步骤", ask_direct(QUESTION))
    show("C 原生思考 —— 步骤在另一个字段", ask_native_thinking(QUESTION))
    show("C' 同一句话、不给草稿纸（思考关）", ask_native_thinking(QUESTION, thinking=False))


if __name__ == "__main__":
    compare()
