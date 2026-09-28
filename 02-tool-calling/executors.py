"""02-0 工具的实际执行逻辑

目标：写三个**真会跑**的普通 Python 函数。这个文件里没有任何 LLM 相关的东西 ——
它就是三个平常的函数，可以单独测、单独调用。

这一点值得停下来想一秒：**工具不是"AI 的东西"，它就是你的代码。**
模型只是给了你一个函数名和一串参数，剩下的全是普通编程。

    模型说："我想调 get_weather，location=北京"
    你的代码：查 name → 找到函数 → 解析 arguments → 调用 → 拿返回值 → 塞回消息

验收标准（详见 ./README.md「先写 3 个工具」）：
  [ ] calculate(expression) —— 能算 '20+15-5' 这种表达式
  [ ] get_weather(city)    —— 先返回假数据就行（这一章的重点不是接真 API）
  [ ] read_file(path)      —— 路径不存在时**抛异常**，这是故意的（03 要拿它做实验）

--- 关键 API ---

  没有 API。就是三个函数。唯一要记住的约定：

      **返回值必须是字符串。**

  因为工具结果要作为 `content` 塞回消息里，而消息的 content 是文本。
  你想返回 dict / list，自己 `json.dumps()` 成字符串再返回 ——
  这一步别指望 SDK 替你转。

--- 三个函数各自的设计点 ---

  · `calculate(expression)`：**绝对不要用 `eval()`。**
    expression 是**模型生成的字符串**，会传给 eval 就等着被注入吧
    （模型能输出 `__import__("os").system("...")` 这种东西）。
    用一个只认四则运算的小解析器，或者白名单式的 ast 求值。这条是安全底线，
    不是风格问题。

  · `get_weather(city)`：返回假数据完全没问题。但**别随机** ——
    随机数会让 03 章的重试做不了（重试时结果变了，分不清是重试起作用还是数据变了）。
    写死一个合理值，比如 "28°C，晴"。

  · `read_file(path)`：**路径不存在就抛 `FileNotFoundError`**，不要自己 catch 掉
    返回 "读取失败"。这一章 03 的实验要观察"异常被当成工具结果发回去"，
    在 executor 里把异常吞了，模型就看不到真实错误了。
    抛异常怎么变成"错误结果"，是调用方（01/02/03 脚本）的事。

--- 坑 ---

  · **返回值必须是 `str`。** 返回 dict 不会报错，但模型看到的是 Python 的
    repr（单引号那种），会理解得含糊。
  · **别在 executor 里 catch 异常。** 异常往上抛，由脚本决定要不要转成错误结果。
    在这里吞掉，01/03 的对照实验就做不成了。
  · `read_file` 别真去读一个敏感路径。给自己留个固定的小目录，
    或者干脆限定在 `02-tool-calling/` 下面。模型会请求读各种路径，别让它读到家。

--- 你要做的 ---

  1. 把三个函数体的 `raise NotImplementedError` 换成实现
  2. 在文件末尾把 EXECUTORS 填上（把 name 映射到函数）——
     01~04 四个脚本都要靠它把 `tool_call.function.name` 变成能调用的函数
"""

from collections.abc import Callable


def calculate(expression: str) -> str:
    """计算一个数学表达式，返回结果字符串。

    参数是**模型生成的字符串**。别用 eval —— 用一个只认四则运算的求值方式。
    算不出来（语法错、除零）就让它抛异常，别自己编一个结果。
    """
    raise NotImplementedError


def get_weather(city: str) -> str:
    """返回某个城市的当前天气。

    这一章用假数据就行，但**要写死**，别用 random ——
    03 章要靠重复调同一个工具来观察模型的反应，结果每次都变的话就观察不了。
    """
    raise NotImplementedError


def read_file(path: str) -> str:
    """读一个文本文件，返回内容。

    路径不存在时**抛 FileNotFoundError**（不 catch）——
    03 章专门拿它来测"工具失败时模型怎么办"。
    """
    raise NotImplementedError


# name → 函数 的映射。
#
# 脚本里拿到的是字符串 `tool_call.function.name`，得靠这张表找函数：
#
#     msg = EXECUTORS[call.function.name](**args)
#
# key 必须和 tools.py 里每个 function 的 name **完全一致** ——
# 对不上就是 KeyError，而模型不认识的工具名也要走"未知工具"分支（03 会用到）。
EXECUTORS: dict[str, Callable[..., str]] = {}
