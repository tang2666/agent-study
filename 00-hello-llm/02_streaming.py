"""00-2 流式输出

目标：知道流式响应长什么样，尤其是**思考和正文是两条独立的流**这件事。

验收标准（详见 ./README.md）：
  [ ] 文字是"流"出来的，不是一次性出现
  [ ] 把思考过程和正文分两行分别实时打印
  [ ] 从最后一个 chunk 拿到 usage
  [ ] 流式和非流式的 usage 对比一下

--- 关键 API ---

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "..."}],
        stream=True,                      # 打开流式
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        delta.reasoning_content    # 思考过程的一片
        delta.content              # 正文的一片

  官方文档给的累加写法就是这么写的：两个字段分别累加，不要混在一起。

--- 三个必须知道的细节 ---

1. 思考先流完，正文才开始流。所以你会先看到一大段 reasoning_content，
   然后 content 才开始有内容。别以为是卡住了。

2. **usage 挂在最后一个 chunk 上**，不是单独发一个只有用量的 chunk。
   官方原文：最后一个 chunk 的 choices 数组里正好一个元素，
   它不带新内容，但带非空的 finish_reason，以及整个请求的 usage。
   所以想拿用量就得在循环里一直更新，循环结束后用最后那个。

   还有个小口子：stream_options={"include_usage": True} 可以让每个 chunk
   都带 usage 字段（除最后一个外都是 null）。不传的话 usage 只在最后一个。
   **注意它必须和 stream=True 一起用，单独传会报 400。**

3. 流以 `data: [DONE]` 结束。SDK 会帮你处理掉这行，不用自己判断。

--- 一个常见的写法错误 ---

  官方示例里有这种写法：

      if chunk.choices[0].delta.reasoning_content:
          reasoning_content += chunk.choices[0].delta.reasoning_content
      else:
          content += chunk.choices[0].delta.content

  能用，但它是"非此即彼"的假设。更稳的写法是两个字段各自判断 is not None：

      if delta.reasoning_content is not None:
          ...
      if delta.content is not None:
          ...

  自己去想一下为什么后者更稳，然后按后者写。
"""

from config import MODEL, client


def stream_answer(question: str) -> None:
    """流式发一次请求，把思考过程和正文**分开**实时打印。

    见 README 的验收标准（详见 ./README.md）。
    """
    raise NotImplementedError("TODO: 实现 stream_answer()")


def nonstream_for_comparison(question: str) -> None:
    """同一个问题，非流式再问一遍，打印 usage，用来和流式的对比。

    见 README 的验收标准（详见 ./README.md）。
    """
    raise NotImplementedError("TODO: 实现 nonstream_for_comparison()")


if __name__ == "__main__":
    stream_answer("用一句话解释什么是 token。")
    print()
    print("=== 下面是同问题的非流式对照 ===")
    nonstream_for_comparison("用一句话解释什么是 token。")
