"""00-4 token 计数与成本估算

目标：对"这次调用要花多少钱"有量级感，并亲眼看到多轮对话的成本是怎么膨胀的。

验收标准（详见 ./README.md）：
  [ ] 能用字符比例估算一段文本的 token 数
  [ ] 拿真实响应的 usage 跟估算对比，看差多少
  [ ] 算出一次调用花多少钱（要区分缓存命中 / 未命中）
  [ ] 算出"第 10 轮比第 1 轮贵几倍"

--- 重要：DeepSeek 没有 count_tokens 接口 ---

  这是跟 Claude 一个明显的差别。Claude 有 client.messages.count_tokens()，
  发个请求就能拿到准确数字。DeepSeek **没有**对应的东西。你只有三条路：

  1. 字符比例估（最快，够用）
     官方给的换算：1 个英文字符 ≈ 0.3 token，1 个中文字符 ≈ 0.6 token
  2. 官方离线 tokenizer（最准，但要额外折腾）
     文档的 Token & Token Usage 页提供了一个 deepseek_tokenizer.zip，
     里面有示例代码，可以在本地精确算
  3. 从真实响应里读（唯一权威）
     response.usage 里就是这次实际用了多少

  官方原话：不同模型的分词方式不同，换算比例会有出入，
  **以模型返回的 usage 为准**。

--- usage 里有什么（官方 API 参考）---

    usage.prompt_tokens              输入总 token 数
                                     == prompt_cache_hit_tokens + prompt_cache_miss_tokens
    usage.completion_tokens          输出总 token 数
    usage.total_tokens               两者之和
    usage.prompt_cache_hit_tokens    命中缓存的输入 token 数   ← 便宜 50 倍
    usage.prompt_cache_miss_tokens   没命中缓存的输入 token 数
    usage.prompt_tokens_details.cached_tokens
    usage.completion_tokens_details.reasoning_tokens   ← 思考花的 token

  注意最后那个 reasoning_tokens：思考模式开着时，模型"想"的那些字
  **也是按输出计费的**。所以思考模式和成本直接相关。

--- 定价（官方定价页，单位：美元 / 每 100 万 token）---

  deepseek-flash（本项目在用的）：
      输入 · 缓存命中     $0.003        输入 · 未命中    $0.15
      输出                $0.60

  deepseek-v4-pro：
      输入 · 缓存命中     $0.022        输入 · 未命中    $0.66
      输出                $1.98

  高峰时段价格是上面的 **2 倍**，非高峰是半价。
  高峰 = UTC 01:00-04:00 和 06:00-10:00，周一至周五，不含中国法定节假日。
  其余时间（含周末和中国法定节假日全天）都是非高峰。

--- 这一节最该记住的一个数字 ---

      缓存命中 $0.003  vs  缓存未命中 $0.15  →  差 50 倍

  同一个 prompt，命中缓存和没命中差 50 倍价钱。
  这就是为什么"把稳定内容放前面"（根 README 约定 4）值得单独记一条。
  你多轮对话里不断变长的历史，如果前缀稳定，绝大部分都是命中缓存的。

--- 成本怎么算 ---

      cost = (hit_tokens  * 0.003
            + miss_tokens * 0.15
            + completion_tokens * 0.60) / 1_000_000

  单位是美元，除以 1e6 是因为定价是按"每百万"给的。
"""

from config import MODEL, client

# 官方定价，美元 / 每 1M token。写成常量，方便你改。
PRICE = {
    "cache_hit": 0.003,
    "cache_miss": 0.15,
    "output": 0.60,
}


# 人民币汇率，粗估用，想改就改
CNY_RATE = 7.1

# 模拟时每轮都发这一句，固定不变，方便对比每轮的输入 token
SIM_QUESTION = "再说一句关于 token 的话，不要重复上一轮的。"

# CJK（中日韩）字符的 Unicode 区间。落在这里面的按 0.6/字符 算，其余按 0.3。
CJK_RANGES = (
    (0x3000, 0x303F),  # CJK 标点
    (0x3040, 0x30FF),  # 日文平假名 + 片假名
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0x4E00, 0x9FFF),  # CJK 基本区（绝大多数汉字）
    (0xAC00, 0xD7AF),  # 韩文谚文
    (0xF900, 0xFAFF),  # CJK 兼容表意
    (0xFF00, 0xFFEF),  # 全角字符
)


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in CJK_RANGES)


def estimate_tokens(text: str) -> int:
    """用字符比例粗估 token 数（英文 0.3/字符，中文 0.6/字符）。

    只是"估"。真实数字以 response.usage 为准 —— 官方自己也是这么说的。
    """
    total = 0.0
    for ch in text:
        total += 0.6 if _is_cjk(ch) else 0.3
    return round(total)


def cost_of(usage) -> float:
    """按上面的公式，从 usage 算这次调用的美元成本。

    usage 是 response.usage 那个对象，从里面读上面列的字段。
    注意：流式和非流式拿 usage 的方式不同（见 02）。
    """
    # 这两个是 DeepSeek 的**自定义字段**，不在 OpenAI 的标准 usage 里。
    # 用 getattr 取，万一哪天没有就退回 0，不至于直接崩。
    hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
    miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
    if hit == 0 and miss == 0:
        # 没有任何缓存信息时，保守一点，输入全按未命中算（贵的那档）
        miss = usage.prompt_tokens

    return (
        hit * PRICE["cache_hit"]
        + miss * PRICE["cache_miss"]
        + usage.completion_tokens * PRICE["output"]
    ) / 1_000_000


def simulate_rounds(n: int = 10) -> None:
    """模拟 n 轮对话，打印每轮的输入 token 数和人民币/美元成本。

    重头戏：看输入 token 怎么随轮次涨。
    因为每轮都要重发全部历史，第 k 轮塞进去 2k-1 条消息，
    累计输入 ≈ n²/2 —— **平方级增长**。
    """
    question = SIM_QUESTION

    messages: list = []
    total_cost = 0.0
    first_prompt = 0
    last_prompt = 0

    header = (
        f"{'轮次':>4} {'消息数':>6} {'输入':>7} {'命中':>7} "
        f"{'未命中':>7} {'输出':>6} {'本轮$':>10} {'累计$':>10}"
    )
    print(header)
    print("-" * len(header))

    for r in range(1, n + 1):
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )

        usage = response.usage
        cost = cost_of(usage)
        total_cost += cost

        hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0
        if r == 1:
            first_prompt = usage.prompt_tokens
        last_prompt = usage.prompt_tokens

        print(
            f"{r:>4} {len(messages):>6} {usage.prompt_tokens:>7} {hit:>7} "
            f"{miss:>7} {usage.completion_tokens:>6} "
            f"{cost:>10.6f} {total_cost:>10.6f}"
        )

        messages.append(response.choices[0].message)

    print("-" * len(header))
    print(f"累计成本：${total_cost:.6f}  ≈ ¥{total_cost * CNY_RATE:.4f}")
    print(
        f"输入 token：第 1 轮 {first_prompt} → 第 {n} 轮 {last_prompt}，"
        f"涨了 {last_prompt / first_prompt:.1f} 倍"
    )


if __name__ == "__main__":
    print(f"估算示例：hello world 你好世界 → {estimate_tokens('hello world 你好世界')} token")
    print(f"下面每轮发的问题：{SIM_QUESTION!r}")
    print(f"纯文本估算是 {estimate_tokens(SIM_QUESTION)} token，"
          f"跟下表第 1 轮的「输入」对比一下，看差多少。\n")
    simulate_rounds(10)
