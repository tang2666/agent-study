"""00-1 最小可用调用（非流式）

目标：跑通一次请求，并**看清 response 的原始结构**。
     这一节的产出不是"能跑"，而是你能指着字段说出每个是干什么的。

验收标准（详见 ./README.md）：
  [ ] 能跑出结果
  [ ] 打印完整的 response，看清 content / reasoning_content / usage / finish_reason / model
  [ ] 能说出 finish_reason 的 6 个可能取值，各自什么含义

--- 关键 API（官方文档的写法，不是老教程里的 Claude 写法）---

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "..."}],
        # max_tokens 可以不传：默认 8K(非思考) / 64K(思考)
        # 思考模式本来就是默认开着的，下面这行只是显式写出来
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

  注意 DeepSeek 是 OpenAI 兼容接口，所以是 client.chat.completions.create，
  不是 anthropic 的 client.messages.create。

  response.choices[0].message.content            # str，正文
  response.choices[0].message.reasoning_content  # str，思考过程（只有思考模式有）
  response.choices[0].finish_reason              # 见下面 6 个取值
  response.usage                                 # token 统计，见 04
  response.model                                 # 实际服务的模型名

--- finish_reason 的 6 个取值（官方 API 参考原文）---

    stop                        自然结束，或撞上了你给的 stop 序列
    length                      撞上 max_tokens 上限，或对话超出最大上下文
    content_filter              内容被内容过滤器拦掉了
    tool_calls                  模型要调用工具（02 章开始会天天见）
    insufficient_system_resource 推理系统资源不足，请求被打断
    aborted                     生成被中断

  只有 stop 和 tool_calls 是"正常"结束。看到 length 要知道输出被截断了。

--- 关于 thinking 参数为什么要塞进 extra_body ---

  openai SDK 只认它自己知道的参数。thinking 是 DeepSeek 自己加的字段，
  SDK 不认识，直接当关键字参数传会报 TypeError。
  extra_body={...} 是 SDK 留给"厂商自定义字段"的口子，会被原样塞进请求 JSON。

  而 reasoning_effort 不一样 —— 它是 OpenAI 后来收编的标准参数，
  所以能直接当关键字参数传，不用包 extra_body。
"""
from config import MODEL, client


def ask(question: str) -> None:
    """发一次请求，并把 response 的完整结构打印出来。

    你要做的：
      1. 用上面「关键 API」里的形状发一次请求
      2. 把整个 response 打印出来（不要只打印文本）
      3. 单独把 content / reasoning_content / finish_reason / model 各打印一行
      4. 再把 usage 整个打印出来
      5. 观察：reasoning_content 和 content 哪个先出现？内容上有什么区别？

    小提示：非思考模式下 message 上**根本没有** reasoning_content 这个属性，
    直接访问会 AttributeError（**不是 None**）。要安全取值就用
    getattr(message, "reasoning_content", None)。
    （只有**流式**的 chunk 里它才是显式的 null，两者不一样。）
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    print(response.model_dump_json(indent=2))
    print(response.choices[0].message.content)
    print(response.choices[0].message.reasoning_content)
    print(response.choices[0].finish_reason)
    print(response.usage)
    print(response.model)


if __name__ == "__main__":
    ask("用一句话解释什么是 token。")
