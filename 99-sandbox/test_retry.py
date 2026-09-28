"""验证 05_errors.call_with_retry 的三条路径。

用一个假的 client 顶替真的，通过让 create() 按次数抛不同异常来测：
  1. 限流 → 应该退避重试，最终成功
  2. 400 → 不该重试，直接抛，只请求 1 次
  3. 一直限流 → 重试 max_retries 次后放弃并抛
"""

import importlib.util
import sys
import time
from pathlib import Path

import httpx2 as httpx  # openai 3.x 内置改名的 httpx
from openai import BadRequestError, RateLimitError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "00-hello-llm"))

spec = importlib.util.spec_from_file_location("e05", ROOT / "00-hello-llm" / "05_errors.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _http_error(cls, status, msg):
    req = httpx.Request("POST", "http://fake")
    resp = httpx.Response(status, request=req)
    return cls(msg, response=resp, body=None)


class FakeClient:
    """前 fail_times 次抛 RateLimitError，之后返回一个假响应。"""

    def __init__(self, fail_times, exc_factory):
        self.fail_times = fail_times
        self.exc_factory = exc_factory
        self.calls = 0

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc_factory()
        return f"<第 {self.calls} 次请求成功>"


def run(label, fake, max_retries=3):
    m.client = fake
    print(f"\n=== {label} ===")
    t0 = time.monotonic()
    try:
        print("结果：", m.call_with_retry([{"role": "user", "content": "x"}], max_retries))
    except Exception as e:  # noqa: BLE001 - 测试里就是要看抛什么
        print(f"抛出：{type(e).__name__}")
    print(f"实际请求次数：{fake.calls}   耗时：{time.monotonic() - t0:.1f}s")


run(
    "1) 限流 2 次后成功 —— 预期睡 1s+2s，共请求 3 次",
    FakeClient(2, lambda: _http_error(RateLimitError, 429, "rate limited")),
)

run(
    "2) 400 BadRequest —— 预期不重试，只请求 1 次",
    FakeClient(99, lambda: _http_error(BadRequestError, 400, "bad request")),
)

run(
    "3) 一直限流 —— 预期请求 4 次(1+3重试)、睡 1+2+4=7s 后放弃",
    FakeClient(99, lambda: _http_error(RateLimitError, 429, "rate limited")),
)
