"""00-5 错误处理

目标：分清"该重试"和"重试也没用"。

验收标准（详见 ./README.md）：
  [ ] 用**具体的异常类**分别捕获，不要一个 except Exception 全接
  [ ] 对限流做指数退避重试（1s → 2s → 4s）
  [ ] 对 400 类错误**不要**重试，直接报错退出
  [ ] 能说出哪些错误重试有意义、哪些没有

--- 关键 API：异常类 ---

    from openai import (
        APIConnectionError,    # 网络问题 —— 重试有意义
        APITimeoutError,       # 超时 —— 重试有意义
        RateLimitError,        # 429 限流 —— 重试有意义，而且要退避
        APIStatusError,        # 其他 HTTP 错误，看 .status_code
        NotFoundError,         # 404，比如模型名写错 —— 重试没用
        BadRequestError,       # 400 参数错 —— 重试没用
        AuthenticationError,   # 401 key 不对 —— 重试没用
    )

  写一条「最具体 → 最宽泛」的异常链：

      try:
          ...
      except NotFoundError:        # 4xx 的一种，重试没用
          ...
      except RateLimitError:       # 要退避重试
          ...
      except APIStatusError as e:  # 兜住其余 HTTP 错误，读 e.status_code
          ...
      except APIConnectionError:   # 网络，可重试
          ...

  顺序不能反 —— 父类写在前面会把子类吞掉。

--- 继承关系（实测 openai 3.19.2 的源码，不是猜的）---

    BadRequestError             400
    AuthenticationError         401
    PermissionDeniedError       403
    NotFoundError               404
    ConflictError               409
    UnprocessableEntityError    422
    RateLimitError              429
    InternalServerError         5xx
        这些**全部**是 APIStatusError 的子类

    APIStatusError          -> APIError
    APIConnectionError      -> APIError
    APITimeoutError         -> APIConnectionError     ← 注意，它是连接的子类
    APIError                -> OpenAIError -> Exception

  所以：先 `except APIStatusError` 的话，RateLimitError / NotFoundError
  会被全部吞掉，永远进不去自己的分支。**最具体的写最前面。**

  APIConnectionError 和 APIStatusError 是**兄弟**（都挂在 APIError 下），
  它俩之间顺序无所谓，但都必须在 APIError 之前。

--- DeepSeek 的 7 个错误码，和 SDK 类怎么对上 ---

    从 SDK 源码读出来的映射规则（openai/_client.py 的 _make_status_error）：

        400 -> BadRequestError
        401 -> AuthenticationError
        403 -> PermissionDeniedError
        404 -> NotFoundError
        409 -> ConflictError
        422 -> UnprocessableEntityError
        429 -> RateLimitError
        >=500 -> InternalServerError
        其他 -> APIStatusError 兜底

    DeepSeek 官方文档列的 7 个码，对过来是：

        400 Invalid Format             -> BadRequestError       不可重试
        401 Authentication Fails       -> AuthenticationError   不可重试
        402 Insufficient Balance       -> **APIStatusError**    不可重试
        422 Invalid Parameters         -> UnprocessableEntityError 不可重试
        429 Rate Limit Reached         -> RateLimitError        可重试（退避）
        500 Server Error               -> InternalServerError   可重试
        503 Server Overloaded          -> InternalServerError   可重试

    **注意 402 那一行**：SDK 里没有为 402 准备专门的类，
    它会落到兜底的 APIStatusError。所以你想优雅地提示"余额不足"，
    得自己判断 `e.status_code == 402`。
    这是个很实际的坑 —— 本地调试时最容易撞上的就是它。

--- 别漏了：客户端错误不是 API 错误 ---

  有些错误在**请求发出之前**就抛了，不在上面那条异常链里，
  所以 `except APIStatusError` 永远接不到：

    TypeError    参数名写错 / 类型不对
    ValueError   参数值非法

  这类错误**重试毫无意义** —— 是代码问题，应该让它直接崩出来让你看见。

  另外还有两个挂在 OpenAIError 下、但**不在** APIError 下的：
    LengthFinishReasonError        （用结构化解析时，输出被 max_tokens 截断）
    ContentFilterFinishReasonError （内容被过滤）
  它们接不到 APIStatusError，要用就拿 OpenAIError 接。

--- 怎么构造这几种失败（2026-09-27 实测，openai 3.19.2 + DeepSeek）---

  **注意：下面有两条和「直觉映射」对不上，是这章最值钱的发现。**

    AuthenticationError(401)        ：把 API Key 改成一个错的
    BadRequestError(400)            ：**模型名写错**。DeepSeek 用的是 400，
                                      不是常见的 404 —— SDK 里根本没有
                                      NotFoundError 给你接，别照抄别家的表
    UnprocessableEntityError(422)   ：**这一档特别宽**，以下全都落 422：
                                        · 消息缺 role / content
                                        · messages 给成字符串（类型就不对）
                                        · 参数值非法，比如 max_tokens=-1
                                      所以「缺字段」并不总是 400
    APIConnectionError              ：把 BASE_URL 指向一个连不上的地址
                                      （注意它**没有** status_code，是 None）
    TypeError                       ：参数名写错。请求根本没发出去，
                                      不在这条异常链上，重试毫无意义
    RateLimitError(429)             ：短期连发大量并发请求（未实测）
    APITimeoutError                 ：服务端迟迟不响应（未实测）
    402                             ：不建议专门去试（要真把余额花光）

  结论：**别背「哪个错误是 400」这种表，动手跑一遍。**
  文档给的是 SDK 的「状态码 → 异常类」映射，不等于「哪种错误 → 状态码」。

--- 重试的两条铁律 ---

  1. 指数退避：1s → 2s → 4s，别用固定间隔，会加剧雪崩
  2. 设上限：重试 3 次还不行就放弃并抛出。
     无限重试在真的故障时只会把账单推高
"""

import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
    UnprocessableEntityError,
)

from config import BASE_URL, MODEL, client

# 「重试有意义」的一组：都是临时性故障，等一会儿可能就好了。
# 这四个里 RateLimitError 和 InternalServerError 是 APIStatusError 的**子类**，
# 所以这个元组必须写在 `except APIStatusError` 前面，否则会被父类那一支整个吞掉。
RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


def call_with_retry(messages: list, max_retries: int = 3) -> object:
    """带指数退避的调用。

    退避节奏 1s → 2s → 4s（2 ** attempt）。用固定间隔会加剧雪崩：
    服务端已经过载了，所有客户端还同步地每秒捶一次。
    """
    # attempt 取 0..max_retries，即「初次尝试 + max_retries 次重试」
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )

        # 临时性故障 → 退避重试
        except RETRYABLE_ERRORS as e:
            if attempt == max_retries:
                # 次数用完还是失败，原样抛出去（裸 raise），别写成死循环
                print(f"× 已重试 {max_retries} 次仍失败，放弃：{type(e).__name__}")
                raise
            wait_seconds = 2**attempt
            print(
                f"↻ 第 {attempt + 1}/{max_retries} 次重试："
                f"{type(e).__name__} → 等 {wait_seconds}s"
            )
            time.sleep(wait_seconds)

        # 其余 HTTP 错误（400/401/402/404/422…）→ 代码或参数问题，重试无用
        except APIStatusError as e:
            if e.status_code == 402:
                # 402 没有专属异常类，会落到 APIStatusError，只能自己看状态码
                print("！余额不足（402）：https://platform.deepseek.com")
            print(f"× 不可重试（{e.status_code} {type(e).__name__}）")
            raise


def break_it() -> None:
    """把各种失败各构造一次，打印异常类名、status_code 和 message。"""
    messages = [{"role": "user", "content": "你好"}]

    # ① 401 —— API Key 是错的。用一个单独的 client，不动全局那个
    try:
        bad_key_client = OpenAI(api_key="sk-this-key-is-wrong", base_url=BASE_URL)
        bad_key_client.chat.completions.create(model=MODEL, messages=messages)
    except AuthenticationError as e:
        print(f"① {type(e).__name__}  status_code={e.status_code}\n   {e}\n")

    # ② 模型名不存在 —— 实测是 400，不是 404
    try:
        client.chat.completions.create(model="deepseek-not-exist", messages=messages)
    except BadRequestError as e:
        print(f"② {type(e).__name__}  status_code={e.status_code}\n   {e}\n")

    # ③ 消息缺 content 字段 —— 实测 422，就是 03_multiturn 撞过的那个
    try:
        client.chat.completions.create(model=MODEL, messages=[{"role": "user"}])
    except UnprocessableEntityError as e:
        print(f"③ {type(e).__name__}  status_code={e.status_code}\n   {e}\n")

    # ④ messages 的整体类型就不对 —— 也是 422
    try:
        client.chat.completions.create(model=MODEL, messages="你好")
    except UnprocessableEntityError as e:
        print(f"④ {type(e).__name__}  status_code={e.status_code}\n   {e}\n")

    # ⑤ 参数值超出合法范围 —— 还是 422
    try:
        client.chat.completions.create(model=MODEL, messages=messages, max_tokens=-1)
    except UnprocessableEntityError as e:
        print(f"⑤ {type(e).__name__}  status_code={e.status_code}\n   {e}\n")

    # ⑥ 连不上 —— 注意 APIConnectionError 没有 status_code 这个属性
    try:
        dead_client = OpenAI(api_key="sk-whatever", base_url="http://127.0.0.1:1")
        dead_client.chat.completions.create(model=MODEL, messages=messages)
    except APIConnectionError as e:
        status = getattr(e, "status_code", None)
        print(f"⑥ {type(e).__name__}  status_code={status}\n   {e}\n")

    # ⑦ 参数名写错 —— 请求根本没发出去，抛的是 TypeError，不在 openai 异常链上
    try:
        client.chat.completions.create(
            model=MODEL, messages=messages, not_a_real_param=1
        )
    except TypeError as e:
        print(f"⑦ {type(e).__name__}（客户端错误，请求没发出去）\n   {e}\n")

    print("没实测的：429 限流、超时（构造成本高）；402（要真把余额花光）")


if __name__ == "__main__":
    break_it()
