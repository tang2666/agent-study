# 90 — 论文与源码笔记

穿插进行，不用等到最后。**建议在对应阶段做完之后立刻读对应的那篇** —— 那时候你有实操经验，能读懂它在说什么；读早了只会觉得"这我也知道啊"。

## 每篇笔记建议的结构

每篇笔记单独一个 `.md`，固定四个部分：

```markdown
# <论文/项目名>

## 它要解决什么问题
（一句话。说不出来说明你还没读懂）

## 核心做法
（用自己的话，不要抄摘要）

## 和我手写的版本对比
（我哪一步是和它一样的？哪一步它做得比我好？）

## 我现在用得上 / 用不上
（诚实点。很多论文的想法在工程上不划算）
```

最后一部分最重要 —— 论文是**研究**，不是工程指南。看懂和采用是两件事。

## 和阶段的对应

| 读这个 | 在哪个阶段之后 |
|---|---|
| Chain-of-Thought 那篇 | `01-prompting` |
| ReAct 那篇 | `03-agent-loop` ★ |
| Reflexion / Self-Refine | `06-patterns` |
| Lost in the Middle | `04-memory` 或 `05-rag` |
| RAG 原论文 | `05-rag` |
| Toolformer | `02-tool-calling` |
| MCP 官方规范 | `08-mcp` |
| 相关 SDK 的源码 | `09-frameworks` |

## 阅读清单

**提示词与推理**
- Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (Wei et al., 2022) —— CoT 的起点
- Tree of Thoughts: Deliberate Problem Solving with Large Language Models (Yao et al., 2023) —— 把"想一次"变成"多想几路"

**Agent 循环**
- **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., 2022) —— `03` 的理论原型，必读
- Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023) —— 反思模式的来源
- Self-Refine: Iterative Refinement with Self-Feedback (Madaan et al., 2023) —— 和 Reflexion 对比着看

**工具与检索**
- Toolformer: Language Models Can Teach Themselves to Use Tools (Schick et al., 2023)
- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020) —— RAG 原论文
- **Lost in the Middle: How Language Models Use Long Contexts** (Liu et al., 2023) —— 读完你会重新考虑"把东西塞上下文"这件事

**协议与规范**
- MCP 官方规范（modelcontextprotocol.io）—— 读规范，不要只读教程
- Anthropic 的工程博客 "Building effective agents" —— 讲什么时候**不该**用 Agent，很值

**源码**
- 你正在用的 SDK 本身。挑一个你好奇的地方读进去：流式是怎么实现的？工具循环是怎么管的？
- 一个你用的 Agent 框架的核心源码。看它的循环和你 `03` 写的差在哪

> 论文版本迭代很快，上面的标题和结论在搜索时可能已经有更新版本。以你实际读到的为准。

## 笔记文件

自己按 `论文名.md` 建文件，比如 `react.md`、`lost-in-the-middle.md`。

- [ ] `react.md`
- [ ] `reflexion.md`
- [ ] `lost-in-the-middle.md`
- [ ] `rag-original.md`
- [ ] `mcp-spec.md`
- [ ] `sdk-source.md`
