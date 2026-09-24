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

--- 怎么构造这几种失败 ---

  - AuthenticationError ：把 DEEPSEEK_API_KEY 改成一个错的
  - BadRequestError(400) ：传一个明显非法的参数，比如 messages 里少 role
  - UnprocessableEntityError(422)：传个类型不对的参数值
  - NotFoundError(404)  ：把 model 改成一个不存在的名字
  - RateLimitError(429) ：短期连发大量并发请求
  - APIConnectionError  ：把 BASE_URL 指向一个连不上的地址
  - 402                 ：这个不建议专门去试（要真把余额花光）

  能构造出来的都亲手跑一次，看真实报错长什么样。跑到了，这一章才算做完。

--- 重试的两条铁律 ---

  1. 指数退避：1s → 2s → 4s，别用固定间隔，会加剧雪崩
  2. 设上限：重试 3 次还不行就放弃并抛出。
     无限重试在真的故障时只会把账单推高
"""

import time

from config import MODEL, client


def call_with_retry(messages: list, max_retries: int = 3) -> object:
    """带指数退避的调用。

    你要做的：
      1. 写成上面那条「最具体 → 最宽泛」的异常链
      2. 只有该重试的异常才重试（限流、网络、超时、5xx）
      3. 退避间隔 2 ** attempt 秒（1s, 2s, 4s）
      4. 4xx 直接抛出，不要浪费时间重试
      5. 每次重试打印一行日志，说明"第几次重试、因为什么、等多久"
      6. 记得 max_retries 用完就抛，别写成死循环
    """
    raise NotImplementedError("TODO: 实现 call_with_retry()")


def break_it() -> None:
    """把上面几种失败各构造一次，观察真实报错。

    打印每种情况捕获到的：异常类名、message、status_code（如果有）。

    建议一种一种来 —— 把不跑的注释掉，跑完一种再换下一种，
    不然满屏报错看不清。跑完把输出记到 99-sandbox/ 或 90-notes/ ——
    这些报错以后你会反复见到。
    """
    raise NotImplementedError("TODO: 实现 break_it()")


if __name__ == "__main__":
    break_it()
