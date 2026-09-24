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


def estimate_tokens(text: str) -> int:
    """用字符比例粗估 token 数（英文 0.3/字符，中文 0.6/字符）。

    提示：遍历字符，判断是不是 CJK 字符（中文/日文/韩文）。
    判断方法之一是看 ord(ch) 落在几个 Unicode 区间里。
    中文大致在 0x4E00-0x9FFF。日文假名、韩文谚文怎么算？
    自己拿个主意，然后在下一节跟真实 usage 对一下你的估算准不准。
    """
    raise NotImplementedError("TODO: 实现 estimate_tokens()")


def cost_of(usage) -> float:
    """按上面的公式，从 usage 算这次调用的美元成本。

    usage 是 response.usage 那个对象，从里面读上面列的字段。
    注意：流式和非流式拿 usage 的方式不同（见 02）。
    """
    raise NotImplementedError("TODO: 实现 cost_of()")


def simulate_rounds(n: int = 10) -> None:
    """模拟 n 轮对话，打印每轮的输入 token 数和人民币/美元成本。

    这是这一节的**重头戏**。你要做的：
      1. 从空 messages 开始，循环 n 轮
      2. 每轮发一个固定的、短的问题（比如"再说一句关于 token 的话"）
      3. 每轮把回复 append 回 messages（就是 03 那张做法）
      4. 每轮打印：轮次、messages 长度、本次 prompt_tokens、
         其中命中缓存的多少、成本、累计成本
      5. 算出来：第 10 轮的输入 token 数大概是第 1 轮的几倍？

    观察重点：因为每轮都要重发全部历史，输入 token 随轮次增长是
    **平方级**的（第 k 轮有 ~k 条消息，总共 ~n²/2）。
    同时观察 prompt_cache_hit_tokens —— 大部分历史应该都是命中的。
    """
    raise NotImplementedError("TODO: 实现 simulate_rounds()")


if __name__ == "__main__":
    print("估算示例：", estimate_tokens("hello world 你好世界"))
    simulate_rounds(10)
