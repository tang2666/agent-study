"""02-0 工具的实际执行逻辑

目标：写三个**真会跑**的普通 Python 函数。这个文件里没有任何 LLM 相关的东西 ——
它就是三个平常的函数，可以单独测、单独调用。

这一点值得停下来想一秒：**工具不是"AI 的东西"，它就是你的代码。**
模型只是给了你一个函数名和一串参数，剩下的全是普通编程。

    模型说："我想调 get_weather，city=北京"
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

--- 三个函数都已经写好了 ---

  这一节的任务是跑通往返，不是设计工具。三个实现可以直接单独测：

      uv run python -c "from executors import calculate; print(calculate('20+15-5'))"

  每个实现里都有一个刻意的决定，读一眼 —— 03 章要靠它们做实验：

    · calculate   用 ast 白名单求值，**不是 eval**（见 _eval_node）
    · get_weather 查一张写死的表；未知城市返回"没有数据"而不是编一个
    · read_file   限定在 02-tool-calling/ 目录内；路径不存在就抛 FileNotFoundError
"""

import ast
import operator
from collections.abc import Callable
from pathlib import Path

# ----------------------------------------------------------------- calculate

# 白名单：只有出现在这张表里的运算符才允许执行。
#
# 这就是"不许用 eval"的正解。`ast.parse` 先把字符串解析成**语法树**，
# 然后我们只对"认识的节点"求值，遇到任何别的节点一律抛错。
# eval 则相反 —— 它会把整个字符串当代码跑，包括 __import__ 这种。
_ALLOWED_BINOPS = {
    ast.Add: operator.add,  # +
    ast.Sub: operator.sub,  # -
    ast.Mult: operator.mul,  # *
    ast.Div: operator.truediv,  # /
    ast.FloorDiv: operator.floordiv,  # //
    ast.Mod: operator.mod,  # %
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,  # +5
    ast.USub: operator.neg,  # -5
}


def _eval_node(node: ast.AST) -> int | float:
    """递归求值语法树节点，只认数字和白名单里的运算符。

    注意**没有** `ast.Pow`（也就是 `**`）：`9**9**9` 会让 Python 算到天荒地老，
    等于给了模型一个 DoS 入口。模型真要算幂，让它拆成连乘 ——
    报错会作为工具结果发回去（03 那套）。
    """
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        # bool 是 int 的子类，True / False 也会落到这里，得单独排掉。
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"只支持数字，不支持 {node.value!r}")
        return node.value

    if isinstance(node, ast.BinOp):
        op = _ALLOWED_BINOPS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符：{type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_UNARYOPS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的一元运算符：{type(node.op).__name__}")
        return op(_eval_node(node.operand))

    # 走到这里，说明表达式里有函数调用、下标、变量名之类的东西 —— 一律拒绝。
    # 比如 __import__("os").system("...") 就会落到这一支。
    raise ValueError(f"表达式里有不支持的东西：{type(node).__name__}")


def calculate(expression: str) -> str:
    """计算一个数学表达式，返回结果字符串。

    参数是**模型生成的字符串**，所以这个函数本身就是一个信任边界：
    只做 ast 白名单求值，绝不 eval。语法错 / 除零 / 不支持的运算符
    都让它抛异常，不编结果。
    """
    tree = ast.parse(expression, mode="eval")  # 坏语法在这里抛 SyntaxError
    return str(_eval_node(tree))


# --------------------------------------------------------------- get_weather

# 写死的一张表 —— 不用 random。03 章要靠"重复调同一个工具、拿到同一个结果"
# 来观察模型的行为；结果每次都变的话，就什么都观察不到。
_WEATHER = {
    "北京": "28°C，晴",
    "上海": "31°C，多云",
    "广州": "33°C，雷阵雨",
    "深圳": "32°C，阴",
}

# 模型偶尔会给英文名，顺手归一化一下，省得它因为"没有数据"来回试。
_CITY_ALIASES = {
    "beijing": "北京",
    "shanghai": "上海",
    "guangzhou": "广州",
    "shenzhen": "深圳",
}


def get_weather(city: str) -> str:
    """返回某个城市的当前天气（假数据）。

    未知城市返回"没有数据"，**不编一个** —— 编的话模型会拿假数据继续往下推，
    最后给你一个看着挺像样、其实全错的答案（03 章能看到这种连锁反应）。
    """
    key = city.strip().removesuffix("市").strip()
    key = _CITY_ALIASES.get(key.lower(), key)
    if key in _WEATHER:
        return f"{key}：{_WEATHER[key]}"
    return f"没有 {city} 的天气数据"


# ----------------------------------------------------------------- read_file

# 允许读的根目录 = 本文件所在目录（02-tool-calling/）。
# 路径是**模型**给的，所以必须挡住 ../../ 这种越界。
_BASE_DIR = Path(__file__).resolve().parent


def read_file(path: str) -> str:
    """读一个文本文件，返回内容。

    只允许读 _BASE_DIR 下面的文件，越界抛 PermissionError。
    路径不存在时**抛 FileNotFoundError**（不 catch）——
    03 章专门拿它来测"工具失败时模型怎么办"。
    """
    target = Path(path)
    if not target.is_absolute():
        target = _BASE_DIR / target
    target = target.resolve()

    if target != _BASE_DIR and _BASE_DIR not in target.parents:
        raise PermissionError(f"只允许读 {_BASE_DIR} 目录下的文件：{path}")

    return target.read_text(encoding="utf-8")  # 不存在 → FileNotFoundError


# ------------------------------------------------------------------ 映射表

# name → 函数。
#
# 脚本里拿到的是字符串 `tool_call.function.name`，得靠这张表找函数：
#
#     result = EXECUTORS[call.function.name](**args)
#
# key 必须和 tools.py 里每个 function 的 name **完全一致** ——
# 对不上就是 KeyError，而模型幻觉出来的工具名也要走"未知工具"分支（03 会用到）。
EXECUTORS: dict[str, Callable[..., str]] = {
    "calculate": calculate,
    "get_weather": get_weather,
    "read_file": read_file,
}
