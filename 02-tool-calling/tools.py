"""02-0 工具定义（schema）

目标：写出三个工具的**定义**。注意是"定义"不是"实现" —— 这个文件里没有一行
执行代码，它只是一份说明书，是你要塞进请求里、给模型看的东西。

    你 → 把 TOOLS 塞进请求 → 模型读懂它能调什么 → 决定调哪个 → 返回 tool_calls
                                                          ↑ 到这儿为止，工具**没被执行过**

真正干活的是 executors.py。模型永远不执行你的代码，它只会"请求"你执行 ——
这个区分是整章的根，也是后面所有权限 / 安全 / 沙箱问题的起点。

验收标准（详见 ./README.md「先写 3 个工具」）：
  [ ] 三个工具：一个纯计算（calculate）、一个查"真实"数据（get_weather，可先假数据）、
      一个会失败的（read_file，路径不存在要报错）
  [ ] 每个工具的 description 写的是「什么时候用它」，不是「它是什么」
  [ ] 参数用 JSON Schema 描述，该 required 的写进 required

--- 关键 API ---

  官方形状就这一种，外面**必须**包一层 `{"type": "function", "function": {...}}`：

      TOOLS = [
          {
              "type": "function",
              "function": {
                  "name": "get_weather",
                  "description": "查询指定城市当前的实时天气。当用户询问某地天气、"
                                 "温度、是否下雨时使用。",
                  "parameters": {          # ← 叫 parameters，不叫 input_schema
                      "type": "object",
                      "properties": {
                          "location": {"type": "string", "description": "城市名"}
                      },
                      "required": ["location"],
                  },
              },
          },
      ]

  传进去的时候用 `tools=TOOLS`（跟 `response_format` 一样是顶层参数，不在 body 里）。

--- description 才是重点 ---

  name 只是给代码用来查表的，模型真正据以做决定的是 description。
  它决定了模型**什么时候会想起来用这个工具** —— 写不好，模型要么不用，要么乱用。

      ❌ "获取天气"                 模型不知道什么情况下该用
      ✅ "查询指定城市当前的实时天气。当用户询问某地天气、温度、是否下雨时使用。
          输入城市名，中文或英文均可。"

  区别在于：好的 description 明确了**触发条件**（用户问什么的时候用），
  而不只是复述功能。

--- 坑 ---

  · **`name` 只能用字母数字下划线**，别用中文名。中文名不会报错，但模型调它的时候
    可能拼错，排查起来很痛苦。
  · **`description` 是给模型读的自然语言，不是给人的注释。** 里面写"TODO""待实现"
    之类的废话，模型会当成真的约束。
  · **别把 create/delete/rm 这类危险工具放进来练手。** 模型真的会请求调用它们，
    而执行它们的是你的代码 —— 也就是真的会跑。这一章的三个工具全是只读的。
  · 三个工具名要和 executors.py 里的函数名对得上，脚本靠 name 查函数。

--- 实测记录（2026-09-29）---

  1. 带 `tools` 的请求，**思考模式默认就是开的** —— 什么都不传，`reasoning_content`
     照样有值（实测 65 字）。所以这一章的请求默认都在思考，不是"纯一次前向"。
     要关得显式传 `extra_body={"thinking": {"type": "disabled"}}`。

  2. `tools` 本身不影响这一点：带不带 tools，思考都是默认开着的。

--- 你要做的 ---

  把下面那个列表填成三个真正的工具定义。
"""

# 三个工具的 schema。
#
# 下面是**注释掉的模板** —— 形状照它写，内容自己定，写完把注释去掉。
# 三个都写在这个列表里，脚本统一 `from tools import TOOLS`。
TOOLS: list[dict] = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "calculate",
    #         "description": "计算一个数学表达式。当用户需要做算术、比较数字大小时使用。",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "expression": {
    #                     "type": "string",
    #                     "description": "要计算的表达式，如 '20+15-5'",
    #                 }
    #             },
    #             "required": ["expression"],
    #         },
    #     },
    # },
    # ... 再写两个：get_weather / read_file
]
