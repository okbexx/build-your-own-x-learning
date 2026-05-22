---
day: 30
topic: Capstone - Personal AI Computer
status: done
date: 2026-05-22
---

# Day 30 - Capstone: Personal AI Computer

## 1. 引言

30 天的最后一天，我们把前面搭过的零件收束成一台自托管 AI 工作站。

它不是一个聊天框，而是一种可运行、可观察、可约束的个人计算环境。

我称它为 Personal AI Computer。

在这台机器里，模型是推理内核，RAG 是语义文件系统，工具沙箱是执行边界，工作流消息是任务总线。

接入层让 Web、CLI 和 API 都能进入系统，隐私认证层决定谁能看什么、做什么、把什么发到哪里。

这与“把大模型接进应用”不同。

Capstone 的问题不是“模型能不能回答”，而是“系统能不能可靠完成任务”。

一个完整请求至少经过身份识别、意图理解、证据检索、工具选择、执行记录和结果返回。

每一步都要能解释，能复盘，能替换。

本章会把 Day1 到 Day29 的主题放进同一张系统图，再给出一个可运行的最小 Python 示例。

后续你可以替换模型、索引、队列、UI 和权限系统，但不要丢掉边界。

**关键洞见：**Personal AI Computer 的重点不是更会聊天，而是把 AI 放进一套可控、可审计、可演进的个人计算系统。

## 2. 系统全景

先看整体结构。

一个自托管 AI 工作站可以分成七层：接入层、身份层、编排层、推理内核、RAG 子系统、工具沙箱、运维与策略层。

这些层不必一开始都很重，但职责要清楚。

用户请求不应该直接碰模型，模型也不应该直接拥有文件、网络、数据库和 shell 权限。

```text
+--------------------------------------------------------------+
|                 PERSONAL AI COMPUTER                         |
|              self-hosted AI workstation                      |
+--------------------------------------------------------------+

  Web UI             CLI              REST API
    |                 |                  |
    +-----------------+------------------+
                      |
              +-------v--------+
              | Access Gateway |
              | auth/rate/cors |
              +-------+--------+
                      |
              +-------v--------+
              | Orchestrator   |
              | route/plan/log |
              +---+-------+----+
                  |       |
        +---------v+     +v-------------+
        | Inference |    | Workflow Bus |
        | Core      |    | event/state  |
        +----+------+    +------+-------+
             |                  |
        +----v------+    +------v-------+
        | RAG       |    | Tool Sandbox |
        | index/ctx |    | fs/http/code |
        +----+------+    +------+-------+
             |                  |
             +---------+--------+
                       |
          +------------v-------------+
          | Observability / Policy   |
          | logs/metrics/audit/store |
          +--------------------------+
```

接入层负责把不同客户端归一化为统一请求。

编排层负责判断任务应该走普通推理、检索增强、工具调用还是异步工作流。

推理内核生成回答、计划或工具调用，但它不直接执行动作。

RAG 子系统把本地资料转成可引用上下文，工具沙箱把动作放进权限边界。

观测和策略层贯穿全链路，记录每一步发生了什么。

只要接口稳定，系统就能从原型长成产品。

**关键洞见：**好架构不是把所有能力塞进模型，而是让模型、知识、工具、消息和审计各在其位。

## 3. 推理内核：呼应 Day13/14

Day13/14 关注模型推理、上下文、token、延迟和模型适配。

到了 Capstone，推理内核仍然重要，但它只是系统中的一个受控部件。

它的最小接口可以是：

```text
generate(messages, context, tools) -> answer | tool_call | plan
```

这个接口背后可以是 stub、llama.cpp、Ollama、vLLM、Transformers，也可以是远程 API。

上层不应该绑定具体模型供应方，而应该关注输入、输出、延迟、token、错误和 trace。

模型输出不能直接被当成事实。

模型说“我找到了证据”，证据仍然必须来自 RAG。

模型说“命令执行成功”，结果仍然必须来自工具沙箱。

模型说“可以外发”，策略仍然必须由系统判断。

Capstone 里常见的推理策略是多模型路由。

小模型做意图分类和路由，中模型处理日常问答与代码辅助，强模型用于复杂规划和关键复核。

推理内核还要管理上下文预算。

历史消息、RAG 片段、工具日志和系统策略都在争夺窗口。

正确做法是保留必要证据，摘要冗长日志，分离短期上下文和长期记忆。

**关键洞见：**推理内核应是可替换、可约束、可观测的计算部件，而不是拥有系统全部权限的黑盒。

## 4. RAG 子系统：呼应 Day5/6/29

Day5/6 处理切分、embedding 和向量检索，Day29 把 RAG 放进智能体链路。

在 Personal AI Computer 中，RAG 是本地知识的语义入口。

传统文件系统按路径找文件，RAG 按意义找证据。

用户问“上次部署方案里的备份策略是什么”，系统应该去本地索引里取证，而不是靠模型记忆猜。

RAG 的流水线是采集、清洗、切分、索引、召回、重排、注入。

采集读取 Markdown、PDF、代码、网页快照和任务日志。

清洗去掉噪声，同时保留标题、段落、代码块和来源。

切分要尊重语义边界，不能只按固定字符数硬切。

索引可以组合向量、关键词、时间、标签和权限元数据。

召回与重排决定证据质量，注入决定模型能否正确使用证据。

RAG 的三种典型失败是没找到、找错了、找到了但用错了。

没找到时系统应承认缺少证据，找错时要改 query rewrite、metadata filter 或 rerank，用错时要收紧提示词和引用规则。

本地 RAG 的优势是隐私。

工作日志、代码草稿、家庭资料和财务笔记可以留在本机。

但索引本身也要保护，因为 chunk、metadata 和 embedding 都可能泄露语义。

所以 collection、权限、审计和备份加密要从第一版就出现。

**关键洞见：**RAG 不是给模型“塞资料”，而是建立从用户问题到本地证据的可追踪路径。

## 5. 工具沙箱：呼应 Day11/15/18

模型只生成文字不够，工作站必须能行动。

行动意味着工具：读文件、查索引、发请求、跑测试、生成报告、触发任务。

但工具也是风险入口。

模型可能误解用户，构造危险参数，被提示注入诱导，或者进入无限循环。

所以工具必须放进沙箱。

沙箱的第一条规则是显式注册。

只有注册过的工具才能被调用，每个工具都有名称、描述、参数 schema、超时和权限级别。

第二条规则是最小权限。

读文件工具只能读允许目录，写文件工具只能写允许路径，shell 工具默认需要更严格约束。

网络工具要限制域名、方法、响应大小和超时。

第三条规则是可审计。

每次调用记录 request_id、user_id、tool、args、duration、status 和摘要。

第四条规则是可中断。

长任务要有超时，高风险动作要有人类确认，循环调用要有最大步数。

工具循环本质上是一个有预算的 while 循环。

模型输出工具调用，编排层验证名称和参数，沙箱执行工具，结果回到上下文，模型决定继续或结束。

**关键洞见：**工具调用不是让模型获得无限行动力，而是给模型一组受控、可记录、可撤销的执行通道。

## 6. 工作流消息：呼应 Day27/28

Day27/28 的队列和工作流，把一次回答扩展成长期任务。

“总结这份文档”可以同步完成，“每天早上总结昨晚日志”就是工作流。

“扫描整个仓库并生成风险清单”也不适合塞进一次 HTTP 请求。

同步请求会超时，难以重试，难以暂停，也难以展示进度。

工作流层把任务拆成事件。

常见事件包括 `task.created`、`document.index.requested`、`tool.run.completed`、`approval.required`、`task.failed`。

事件进入队列，worker 消费事件，状态写入存储，前端通过轮询、SSE 或 WebSocket 显示进度。

核心不是“异步”，而是状态机。

一个任务至少要有 pending、running、waiting_approval、succeeded、failed、cancelled。

没有状态机，后台执行会变成不可解释的线程。

有了状态机，失败可以恢复，用户能知道系统卡在哪里。

第一版可以用内存队列说明原理。

关键是任务边界要清楚，不要把长任务写成一个巨大函数。

**关键洞见：**工作流消息让 AI 从“回答一次”升级为“可靠完成一个可追踪任务”。

## 7. 接入层：呼应 Day1/2/7/8/22

接入层是 Personal AI Computer 的门面。

入口可以是 Web UI、CLI、REST API，也可以是桌面快捷入口。

不同入口不应该各自实现业务逻辑。

它们应被归一化成统一请求对象，包含 user_id、session_id、message、attachments、client、scope 和 flags。

接入层还要处理流式输出。

模型生成、RAG 检索和工具调用都需要时间。

Web 可以用 SSE 或 WebSocket，CLI 可以逐行打印事件，API 可以返回 task_id 让客户端轮询。

接入层也负责输入归一化。

纯文本进入对话管线，附件进入文档管线，URL 进入抓取管线，语音进入转写管线，多轮历史进入会话管线。

如果系统只跑在 localhost，认证可以简单。

如果进入家庭内网，就需要账号或 token。

如果暴露公网，就需要 HTTPS、强认证、限流、审计和更新策略。

**关键洞见：**接入层不是 UI 附属品，而是把多种入口统一成安全、稳定、可路由请求的边界层。

## 8. 运维可观测

AI 系统不可观测，就不可改进。

普通服务看 QPS、延迟、错误率和资源占用，AI 工作站还要看 prompt 长度、completion 长度、检索命中率和工具调用次数。

还要看循环步数、用户取消率、人工确认次数、远程模型调用次数和证据引用率。

这些指标能直接定位问题。

回答幻觉多，可能是 RAG 召回差，也可能是提示词没有要求引用证据。

延迟高，可能是模型慢、检索慢或工具阻塞。

工具失败多，可能是 schema 不清楚、权限策略太窄或模型调用了不存在的工具。

最小可观测系统需要日志、指标和追踪。

第一版可以用 JSON Lines。

每次请求一行，每次检索一行，每次模型调用一行，每次工具调用一行。

字段包括 request_id、session_id、component、event、duration_ms、status 和 summary。

但先把事件语义定下来。

可观测还要记录版本。

模型版本、提示词版本、索引版本和工具版本都会影响结果。

同一个问题昨天答对，今天答错，没有版本就无法复盘。

**关键洞见：**AI 可观测不只是服务是否存活，还要解释推理、检索、工具和工作流为什么这样运行。

## 9. 隐私认证：呼应 Day24

自托管不自动等于安全。

安全来自边界、策略和审计。

第一层是认证：系统要知道请求是谁发起的。

本机单用户可以用本地 token，多人或公网访问需要账号、强密码和二次验证。

第二层是授权：认证回答“你是谁”，授权回答“你能做什么”。

用户可以问公开知识库，不代表能读私人目录；用户可以用低风险工具，不代表能执行 shell。

第三层是数据分区。

工作资料、私人笔记、代码仓库、财务文档和系统日志不应混在同一无差别索引里。

collection、标签和访问策略要明确。

第四层是外发控制。

如果接远程模型，系统必须知道哪些上下文允许外发。

敏感文档默认 local_only，文档也可以标记 no_external。

第五层是提示注入防护。

RAG 文档和网页内容可能包含恶意指令，系统要把外部内容标记为数据，而不是策略。

检索证据不能覆盖系统提示，工具输出也不能绕过权限。

第六层是密钥管理。

API key、数据库密码和签名密钥不能写进 prompt，也不能进入普通日志。

第七层是审计。

谁访问了哪个 collection，哪个请求调用了远程模型，哪个工具读取了哪个目录，这些都要可查。

**关键洞见：**隐私不是把数据放在本机这么简单，而是能定义并审计数据如何被模型、工具和人访问。

## 10. 最小可运行 capstone

下面是一个最小 Python 示例，包含 FastAPI 接入层、推理 stub、内存 RAG 和工具循环。

保存为 `app.py`，运行 `uvicorn app:app --reload`。

```python
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Personal AI Computer Capstone")

class ChatIn(BaseModel):
    message: str = Field(min_length=1)

class ChatOut(BaseModel):
    answer: str
    trace: list[dict[str, Any]]

@dataclass
class Chunk:
    source: str
    text: str

class TinyRAG:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []

    def add(self, source: str, text: str) -> None:
        parts = re.split(r"\n\s*\n", text.strip())
        self.chunks.extend(Chunk(source, p) for p in parts if p)

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        q = set(re.findall(r"\w+", query.lower()))
        scored: list[tuple[int, Chunk]] = []
        for chunk in self.chunks:
            terms = set(re.findall(r"\w+", chunk.text.lower()))
            score = len(q & terms)
            if score:
                scored.append((score, chunk))
        return [c for _, c in sorted(scored, reverse=True, key=lambda x: x[0])[:k]]

rag = TinyRAG()
rag.add("day13.md", "Day13 explains local inference, adapters, tokens, and latency.")
rag.add("day29.md", "Day29 explains RAG, evidence, tool loops, and orchestration.")
rag.add("policy.md", "Tools must be registered, audited, time limited, and checked.")

def tool_now(_: str) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def tool_rag(query: str) -> str:
    hits = rag.search(query)
    return "\n".join(f"[{h.source}] {h.text}" for h in hits) or "No local evidence found."

TOOLS = {"now": tool_now, "rag": tool_rag}

class StubLLM:
    def generate(self, message: str, context: str) -> str:
        lower = message.lower()
        if "time" in lower or "now" in lower:
            return "[[tool:now ]]"
        if ("rag" in lower or "day" in lower or "policy" in lower) and not context:
            return f"[[tool:rag {message}]]"
        if context:
            return "Evidence:\n" + context
        return "Local inference stub. Replace with Ollama, vLLM, or llama.cpp."

llm = StubLLM()

def run_agent(message: str, max_steps: int = 4) -> ChatOut:
    trace: list[dict[str, Any]] = []
    context = ""
    for step in range(max_steps):
        output = llm.generate(message, context)
        trace.append({"step": step, "component": "llm", "output": output})
        match = re.fullmatch(r"\[\[tool:(\w+)\s*(.*?)\]\]", output, re.S)
        if not match:
            return ChatOut(answer=output, trace=trace)
        name, arg = match.group(1), match.group(2).strip()
        if name not in TOOLS:
            return ChatOut(answer=f"Tool rejected: {name}", trace=trace)
        result = TOOLS[name](arg)
        trace.append({"step": step, "component": "tool", "name": name, "result": result})
        context = result
    return ChatOut(answer="Stopped: tool loop budget exceeded.", trace=trace)

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn) -> ChatOut:
    return run_agent(body.message)
```

这个示例故意朴素。

词项重叠代替 embedding，StubLLM 代替真实模型，内存列表代替向量数据库。

但控制流是真实的：请求进入 API，模型决定是否调用工具，编排层验证工具，工具返回证据，模型基于上下文回答。

trace 记录每一步，这是后续审计和调试的基础。

测试请求如下：

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'content-type: application/json' \
  -d '{"message":"What does Day29 say about RAG?"}'
```

**关键洞见：**最小可运行版本先证明链路正确，再替换更强模型、更好索引和更严沙箱。

## 11. 从原型到产品：对比 Ollama/LangChain/OpenWebUI

Ollama、LangChain 和 OpenWebUI 都有价值，但它们处在不同层。

Ollama 更像模型运行时，解决本地模型下载、启动和 HTTP 调用。

它适合快速获得本地推理能力，但不负责完整 RAG、权限、工作流和审计。

LangChain 更像编排框架，提供 prompt、chain、retriever、tool、agent 和 memory 等抽象。

它适合快速试验复杂链路，但抽象会隐藏细节。

如果你不能解释消息如何流动，调试会变困难。

OpenWebUI 更像用户界面和集成入口，适合快速搭建本地聊天体验。

但深度个人工作流仍然需要自定义后端。

务实路线是先建边界。

先用 stub 或 Ollama 提供推理，再用简单 RAG 管理本地文档，再用 FastAPI 暴露统一接口。

从原型到产品，还要补持久化、迁移、测试、配置、恢复和备份。

会话、索引、任务和审计不能只在内存里。

权限、RAG 召回、工具策略和 API 合约都要测试。

服务重启后，未完成任务要能继续或明确失败。

产品化不是把界面做漂亮，而是让系统在真实使用中可预期。

**关键洞见：**这些工具都能成为组件，但 Capstone 的核心能力来自你自己定义的边界、状态、权限和观测。

## 12. 30 天收束

30 天可以重新整理成一条系统路线。

Day1/2 让服务跑起来。

Day5/6 让知识能被检索。

Day7/8 让应用和接口成形。

Day11/15/18 让模型安全使用工具。

Day13/14 让我们理解推理内核。

Day22 让系统接近真实部署。

Day24 让隐私和认证进入架构。

Day27/28 让长任务拥有消息和状态。

Day29 让 RAG、工具和智能体开始组合。

这个收束不是把所有代码塞进一个大项目。

它是把概念组织成一套可维护架构。

你现在应该能回答：请求从哪里进入，身份在哪里确认，检索在哪里发生，模型在哪里生成，工具在哪里执行。

也应该能回答：长任务在哪里排队，日志在哪里记录，敏感数据在哪里被阻止外发。

如果答案清楚，系统就有了骨架。

后续可以换模型、换向量库、换 UI、换队列、扩权限、加工作流。

但不要丢掉原则。

模型不是系统，RAG 不是系统，工具不是系统，UI 也不是系统。

系统是这些部件在清晰边界内协作。

Personal AI Computer 的长期方向，是让个人重新拥有计算环境的主动权。

它读本地知识，执行重复任务，解释行动轨迹，守住隐私边界，并随着你的资料和习惯逐步变强。

这比单次问答更接近个人计算机的原始精神。

计算机帮助人表达、组织、试验、生产和复盘。

AI 加进去以后，这件事没有改变，只是交互方式变了。

**关键洞见：**30 天的终点不是学完某个框架，而是拥有一套能继续演进的 AI 系统判断力。
