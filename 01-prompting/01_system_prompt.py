"""01-1 system / user 的职责划分

目标：搞清 system prompt 是「角色和规则」，不是「内容」。
     以及它跟 user 消息在职责上、在缓存上的区别。

验收标准（详见 ./README.md）：
  [ ] 同一个问题，写两个 system prompt（一个好一个差），能明确说出差在哪
  [ ] 试验：把重要规则从 system 挪到第一条 user 消息里，输出有区别吗？为什么？
  [ ] 能说出 system prompt 和 user 消息在**缓存**上的区别

--- 关键 API ---

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是……"},   # 角色 / 规则 / 约束
            {"role": "user",   "content": "……"},        # 本次要处理的内容
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

  messages 是个**列表**，system 通常放第 0 条。可以放多条 system，
  也可以一条都不放 —— 都没有硬性要求。

--- 职责怎么分：一个判断标准 ---

  就一句话：**这件事需要用自然语言理解吗？**

  需要自然语言理解 → 写进 prompt（system 或 user）
      「你是资深代码审查员」
      「回答控制在三句话以内」
      「不确定就说不确定，别编」

  用代码判断就行 → 写进代码，别求模型自觉
      「输出必须能 json.loads()」  → response_format（见 02）
      「年龄必须是 0-150 的整数」   → 你自己 validate（见 05）
      「只能取这三个值之一」        → 枚举校验

  把「能用代码保证的事」交给模型自觉遵守，是新手最常见的浪费：
  既不可靠，又白烧 token。

--- system 放最前面，是为了命中缓存 ---

  根 README 约定 4：DeepSeek 的磁盘前缀缓存要求**前缀完整匹配**
  （00 章的 04_tokens 里你已经亲眼看到命中量是按块算的）。
  system 每轮都一样 → 它又在最前面 → 一命中就是一大块。

  这就是「稳定的放前面，会变的放后面」的由来：

      [system 永不变] [工具定义 基本不变] [历史对话 越来越长] [本轮问题 每次都变]
                                                              ↑ 变的东西必须在最后

  反过来，把每次都不一样的内容塞进 system，前缀永远不匹配，缓存一次都命中不了。

--- 别搞混 ---

  · 角色名就 system / user / assistant / tool 四个。老教程里的 "developer"
    之类是别家的写法，DeepSeek 不认。
  · system prompt 不是「写得越详细越好」。规则之间会互相打架，
    20 条规则的 system 常常不如 3 条 —— 这个你跑一次就有感觉。
"""

from config import MODEL, client

# 下面三个常量都留给你自己填。
#
# SYSTEM_GOOD 的要点：给定角色 + 给定输出约束 + 给定「不知道就说不确定」
# SYSTEM_BAD  的要点：空泛 / 自相矛盾 / 或者干脆不写（用 None）
# QUESTION    的要点：挑一个「很容易答得又长又空」的问题，比如「什么是 RAG？」
SYSTEM_GOOD = (
    "你是一个资深程序员，熟练掌握后端开发技能，但是对前端和大模型不熟悉，"
    "别人的问题你需要有理有据，不能凭空捏造，不知道的问题就说不知道"
)
SYSTEM_BAD = "你是一个程序员"
QUESTION = "我要学习开发 ，你有什么建议吗"


def ask_with_system(system_prompt: str, question: str) -> str:
    """带 system prompt 发一次请求，返回正文。

    消息就两条：system + user。别多加东西，不然你分不清是谁起的作用。
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},  # 角色 / 规则 / 约束
            {"role": "user", "content": question},  # 本次要处理的内容
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    print(f"[思考]:{response.choices[0].message.reasoning_content}")
    print(f"[回答]:{response.choices[0].message.content}")
    print(f"[usage]:{response.usage}")


def ask_system_as_user(system_prompt: str, question: str) -> str:
    """把本该放 system 的规则挪到**第一条 user 消息**里，再发一次。

    这是对照实验：输出跟 ask_with_system() 有区别吗？
    想清楚「为什么有/没有区别」比结果本身重要。
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": system_prompt},  # 角色 / 规则 / 约束
            {"role": "user", "content": question},  # 本次要处理的内容
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    print(f"[思考]:{response.choices[0].message.reasoning_content}")
    print(f"[回答]:{response.choices[0].message.content}")
    print(f"[usage]:{response.usage}")


def compare() -> None:
    """跑三种组合，把输出打出来对照。

    1. SYSTEM_BAD  + QUESTION
    2. SYSTEM_GOOD + QUESTION
    3. SYSTEM_GOOD 的内容当成第一条 user 消息（不用 system 角色）

    打印时标清楚每种是哪个，不然一屏输出看不出谁是谁。
    """

    print("这是优秀的系统提示词---")
    ask_with_system(SYSTEM_GOOD, QUESTION)

    print("这是糟糕的系统提示词---")
    ask_with_system(SYSTEM_BAD, QUESTION)

    print("这是把提示词放在了user消息中---")
    ask_system_as_user(SYSTEM_GOOD, QUESTION)



if __name__ == "__main__":
    compare()

"""
实验结论：

1. 好 system 和差 system 差在哪？
   差在「模型的行为空间被限定了多少」，不是文笔或长度。
   · 差 system（"你是一个程序员"）= 等于没约束，模型退回通用助手的默认行为：
     倾向于把推荐列满，而且没有「我不知道」这个出口。所以它会自信地列
     React/Vue、CS50、freeCodeCamp，哪怕它对前端并不比你懂。
   · 好 system 干三件事：给角色 + 给边界（前端/大模型不熟）+ 给诚实条款
     （不知道就说不知道）。输出里就真的出现了「前端我不熟，不装懂」。
   机制：system 是划定「该说什么 / 不该说什么」的判据，判据越明确，模型越
   不容易自由发挥。规则要少而清 —— 20 条互相打架，不如 3 条不冲突的。
   反直觉证据：好 prompt 的回答反而更长（completion 2953 vs 1790）。
   约束的是边界，不是长度。

2. 规则放 system vs 放第一条 user 消息，有区别吗？
   单轮：几乎没区别，两个输出都遵守了角色约束。
   为什么：system 和 user 都是拼进同一个上下文的文本，只是 role 标记不同；
   单轮里 DeepSeek 不会对 system 额外加权到肉眼看得出差别。
   注意 71 vs 72 那个 token 差是噪声 —— 同一段文本换个 role 名，分词差一两个
   很正常，重跑可能就反过来。别在 1 个 token 的差上建结论。
   那 system 的意义在哪？两条：
   · 工程上它是一个独立的、可替换的槽位。换规则 / 加工具定义 / 多租户，
     只改 system 一处，不用去动对话历史。
   · 它是天然的稳定前缀（位置最前 + 内容每轮不变）—— 但第一条 user 消息
     如果也不变，同样能缓存，这不是 system 的特权。
   真正会踩的坑：把规则和本轮问题拼在同一条 user 消息里，问题每轮都变，
   前缀永远匹配不上，缓存一次都不命中。

3. system 和 user 在缓存上的区别？
   机制：DeepSeek 默认开磁盘前缀缓存，按前缀块匹配，要求前缀**完整匹配**。
   命中的输入 token 单价降到约 1/50（$0.003 vs $0.15 per 1M）。
   关键认知：区分的不是「谁是 system」，而是「谁落在稳定的前缀里」。
   正确的组织顺序：
       [system 永不变] [工具定义 基本不变] [历史对话 递增] [本轮问题 每次都变]
                                                              ↑ 变的必须在最后
   两个常见误解（我原文各中了一个）：
   · 不是「不用重复输入」—— 每轮照样把 system 原文完整发出去，一个字没少发。
     缓存省的是**服务端重新计算这段前缀**的钱，不是省了发送。
   · 不是「system 更省 token」—— 省的是**单价**，token 数量一模一样。
   极端反例：把时间戳 / 随机 ID 塞进 system → 前缀永远不匹配 → 命中率恒为 0。
"""