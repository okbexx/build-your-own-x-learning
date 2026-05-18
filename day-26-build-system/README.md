---
day: 26
topic: Build System
status: done
---

# Day 26｜Build System（构建系统）

<div style="background:#070b14;color:#d8e7ff;border:1px solid #1e3a5f;border-radius:8px;padding:18px;">

`Build System` 的本质不是“把命令串起来”，而是把 <mark style="background:#10384a;color:#67e8f9;">源文件</mark>、<mark style="background:#12351f;color:#86efac;">依赖关系</mark>、<mark style="background:#3a2b12;color:#facc15;">构建规则</mark> 和 <mark style="background:#321936;color:#f0abfc;">产物状态</mark> 建模成一张可分析、可缓存、可并行执行的图。

</div>

```text
source files
    │
    ▼
dependency graph
    │
    ▼
incremental planner
    │
    ▼
parallel scheduler
    │
    ▼
artifacts
```

---

## 01. 为什么构建系统值得单独学习

在很小的项目里，构建可能只是一条命令：

```bash
gcc main.c -o app
```

但项目一旦变大，就会出现一组无法靠记忆稳定解决的问题：

- 哪些文件改了，哪些目标必须重新构建？
- `app` 依赖哪些 `.o` 文件，`.o` 文件又依赖哪些 `.h` 文件？
- 多个目标能不能同时构建？哪些必须按顺序等待？
- 构建失败时，是源码错、依赖错、规则错，还是缓存错？
- 为什么本地能构建，CI 上却失败？
- 为什么同样的输入，在不同机器上得到不同产物？

构建系统要解决的核心问题可以压缩成一句话：

> 把“如何从输入得到输出”变成一张机器可推理的依赖图，然后只执行必要、合法、可复现的步骤。

---

## 02. 核心概念

### 2.1 目标：Target

<mark style="background:#10384a;color:#67e8f9;">Target</mark> 是构建系统可以请求构建的对象。它可以是一个真实文件，也可以是一个逻辑任务。

| 类型 | 示例 | 说明 |
|---|---|---|
| 文件目标 | `main.o`、`app`、`bundle.js` | 构建后会生成具体文件 |
| 逻辑目标 | `clean`、`test`、`deploy` | 不一定对应文件，更像命令入口 |
| 聚合目标 | `all`、`release` | 依赖多个子目标，用来组织构建入口 |

一个目标通常由两部分定义：

```makefile
target: dependencies
	command
```

含义是：

```text
要构建 target，必须先确保 dependencies 已经是最新的，
然后执行 command 生成或更新 target。
```

---

### 2.2 规则：Rule

<mark style="background:#3a2b12;color:#facc15;">Rule</mark> 描述“如何构建一个目标”。它回答三个问题：

- 输入是什么？
- 输出是什么？
- 用什么命令或函数把输入变成输出？

例如：

```makefile
main.o: main.c util.h
	gcc -c main.c -o main.o
```

这条规则表达的是：

```text
main.o 依赖 main.c 和 util.h。
如果 main.c 或 util.h 比 main.o 新，就需要重新执行 gcc 命令。
```

构建系统越成熟，规则描述的信息越丰富：

| 信息 | 作用 |
|---|---|
| 输入文件 | 判断是否需要重建 |
| 输出文件 | 记录产物位置 |
| 命令行 | 构建行为本身 |
| 环境变量 | 避免环境变化导致缓存错误 |
| 工具链版本 | 避免编译器变化却复用旧产物 |
| 声明式属性 | 支持远程执行、沙箱、缓存 |

---

### 2.3 依赖图：Dependency Graph

<mark style="background:#12351f;color:#86efac;">依赖图</mark> 是构建系统的骨架。

如果 `app` 依赖 `main.o` 和 `util.o`，而两个 `.o` 文件又依赖源文件和头文件，可以画成：

```text
main.c ───┐
util.h ───┼──> main.o ───┐
          │              │
util.c ───┼──> util.o ───┼──> app
util.h ───┘              │
                         │
link rule ───────────────┘
```

构建系统通常要求这张图是 <mark style="background:#1e1b4b;color:#a5b4fc;">DAG</mark>，也就是有向无环图：

- 有向：边表示“谁依赖谁”
- 无环：不能出现 `A -> B -> C -> A`
- 可排序：可以找到合法的构建顺序

如果出现环，构建顺序就无法成立：

```text
A depends on B
B depends on C
C depends on A
```

这意味着构建 `A` 之前要先构建 `B`，构建 `B` 之前要先构建 `C`，构建 `C` 之前又要先构建 `A`。系统必须报错，而不是猜一个顺序。

---

### 2.4 增量构建：Incremental Build

<mark style="background:#321936;color:#f0abfc;">增量构建</mark> 的目标是：只重建真正过期的目标。

完整构建的思路是：

```text
每次从头构建所有目标。
```

增量构建的思路是：

```text
先判断哪些目标仍然有效，只重建受影响的部分。
```

例如：

```text
修改 util.c
    │
    ▼
util.o 过期
    │
    ▼
app 也过期
    │
    ▼
main.o 不需要重建
```

这就是构建系统最重要的性能来源。大型项目能从几十分钟降到几十秒，靠的往往不是单条命令变快，而是大量目标被正确跳过。

---

### 2.5 并行执行：Parallel Execution

依赖图不仅能决定顺序，也能暴露并行机会。

如果两个目标之间没有依赖关系，它们就可以同时构建：

```text
main.o ───┐
          ├──> app
util.o ───┘
```

`main.o` 和 `util.o` 都完成后才能链接 `app`，但它们彼此独立，因此可以并行执行。

调度器的核心规则是：

```text
一个目标只有在它的所有依赖都完成后，才能进入可执行队列。
```

可以把并行调度想成一个不断变化的队列：

```text
ready queue: [main.o, util.o]
running:     [main.o, util.o]
done:        []

ready queue: [app]
running:     [app]
done:        [main.o, util.o]
```

真实构建器还会考虑 CPU、内存、磁盘 I/O、网络、失败恢复、日志归并和输出隔离。

---

## 03. 经典实现思路

### 3.1 Makefile 风格：规则驱动

Makefile 是最经典的构建系统形态之一。它的语法非常接近构建系统的抽象模型：

```makefile
app: main.o util.o
	gcc main.o util.o -o app

main.o: main.c util.h
	gcc -c main.c -o main.o

util.o: util.c util.h
	gcc -c util.c -o util.o
```

这个文件表达了三层信息：

| 层次 | 内容 |
|---|---|
| 目标层 | `app`、`main.o`、`util.o` |
| 依赖层 | 每个目标依赖哪些文件或目标 |
| 执行层 | 目标过期时运行什么命令 |

Makefile 风格的优点是直接、透明、容易手写。缺点是大型项目中依赖容易漏写，跨平台命令容易分叉，复杂逻辑也容易把构建文件变成脚本泥潭。

---

### 3.2 DAG 调度：从依赖图到执行计划

构建系统拿到规则后，通常会先构建一张 DAG：

```text
rules
  │
  ▼
nodes + edges
  │
  ▼
topological order
  │
  ▼
execution plan
```

最基本的顺序构建可以用 <mark style="background:#10384a;color:#67e8f9;">拓扑排序</mark> 完成。

伪代码如下：

```text
visit(target):
    if target is visiting:
        error "cycle detected"

    if target is already visited:
        return

    mark target as visiting

    for dependency in target.dependencies:
        visit(dependency)

    mark target as visited
    append target to build_order
```

这个算法保证：

```text
每个目标都会出现在它的依赖之后。
```

也就是说，如果 `app` 依赖 `main.o`，那么构建顺序中 `main.o` 一定排在 `app` 前面。

---

### 3.3 时间戳校验：经典但粗糙

传统 `make` 主要依靠文件修改时间判断是否需要重建。

核心判断可以简化成：

```text
if output does not exist:
    rebuild
else if any input.mtime > output.mtime:
    rebuild
else:
    skip
```

优点：

- 实现简单
- 判断速度快
- 对小项目非常实用

缺点：

- 文件内容没变但时间戳变了，会误触发构建
- 文件内容变了但时间戳异常，可能漏构建
- 构建命令变了，时间戳模型不一定能发现
- 编译器版本、环境变量变化，也可能被忽略

时间戳模型适合“文件系统本地构建”，但很难支撑强缓存和远程复用。

---

### 3.4 哈希校验：更接近内容真相

现代构建系统更常用 <mark style="background:#12351f;color:#86efac;">内容哈希</mark> 或 <mark style="background:#12351f;color:#86efac;">动作指纹</mark>。

一个目标的缓存 key 可以由这些信息组成：

```text
hash(
    input file contents,
    command line,
    environment variables,
    compiler version,
    rule definition
)
```

如果 key 没变，说明当前产物仍然可信：

```text
cache key unchanged -> skip or restore artifact
cache key changed   -> rebuild and update cache
```

优点：

- 比时间戳更准确
- 适合本地缓存和远程缓存
- 能把命令、工具链、环境纳入判断

代价：

- 需要读取和哈希输入内容
- 需要明确哪些因素会影响输出
- 规则必须尽量纯净，否则缓存会不可靠

这也是 Bazel、Buck、Nix 等系统强调声明式规则、沙箱和可复现构建的原因。

---

## 04. 构建系统的执行流程

一个典型构建器可以拆成六步：

```text
1. 读取构建文件
2. 解析规则和依赖
3. 构建依赖图
4. 检查循环依赖
5. 判断哪些目标需要重建
6. 按拓扑顺序或并行调度执行
```

更完整的实现会在第 5 步和第 6 步之间加入缓存查询：

```text
target requested
    │
    ▼
load rules
    │
    ▼
build DAG
    │
    ▼
topological planning
    │
    ▼
check freshness / cache
    │
    ├── fresh: skip
    ├── cache hit: restore
    └── stale: execute rule
```

这里最容易出错的地方不是执行命令，而是“判断是否可以不执行命令”。构建系统的复杂度，大多来自正确跳过工作。

---

## 05. 最小可运行 Python 示例

下面是一个极简构建器。它演示三件事：

- 解析 Makefile 风格的 `target: deps`
- 对依赖图做拓扑排序
- 按依赖优先的顺序构建目标

它不会真正调用编译器，而是用 `print` 模拟构建命令，这样可以专注理解依赖图和调度过程。

```python
from __future__ import annotations

import sys
from dataclasses import dataclass


SPEC = """
app: main.o util.o
main.o: main.c util.h
util.o: util.c util.h
"""


COMMANDS = {
    "main.o": "cc -c main.c -o main.o",
    "util.o": "cc -c util.c -o util.o",
    "app": "cc main.o util.o -o app",
}


@dataclass(frozen=True)
class Rule:
    target: str
    deps: list[str]


def parse_rules(text: str) -> dict[str, Rule]:
    """Parse lines like: target: dep1 dep2"""
    rules: dict[str, Rule] = {}

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if ":" not in line:
            raise ValueError(f"line {line_no}: missing ':'")

        target_part, deps_part = line.split(":", 1)
        target = target_part.strip()
        deps = deps_part.split()

        if not target:
            raise ValueError(f"line {line_no}: empty target")

        if target in rules:
            raise ValueError(f"line {line_no}: duplicate target {target!r}")

        rules[target] = Rule(target=target, deps=deps)

    return rules


def topo_sort(root: str, rules: dict[str, Rule]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return

        if node in visiting:
            cycle = " -> ".join(stack + [node])
            raise ValueError(f"cycle detected: {cycle}")

        # A node without a rule is treated as a source file.
        if node not in rules:
            return

        visiting.add(node)
        rule = rules[node]

        for dep in rule.deps:
            visit(dep, stack + [node])

        visiting.remove(node)
        visited.add(node)
        order.append(node)

    visit(root, [])
    return order


def build(root: str) -> None:
    rules = parse_rules(SPEC)
    order = topo_sort(root, rules)

    print("[plan] " + " -> ".join(order))

    for target in order:
        command = COMMANDS.get(target, f"echo build {target}")
        print(f"[build] {target}")
        print(f"        {command}")


if __name__ == "__main__":
    requested_target = sys.argv[1] if len(sys.argv) > 1 else "app"
    build(requested_target)
```

运行方式：

```bash
python mini_build.py app
```

输出示例：

```text
[plan] main.o -> util.o -> app
[build] main.o
        cc -c main.c -o main.o
[build] util.o
        cc -c util.c -o util.o
[build] app
        cc main.o util.o -o app
```

这个输出说明：

- `app` 被请求构建
- 系统先递归访问它的依赖 `main.o` 和 `util.o`
- 源文件 `main.c`、`util.c`、`util.h` 没有构建规则，因此被视为输入叶子节点
- 拓扑排序保证 `app` 一定在两个 `.o` 文件之后构建

如果把规则改成循环依赖：

```python
SPEC = """
a: b
b: c
c: a
"""
```

程序会报错：

```text
ValueError: cycle detected: a -> b -> c -> a
```

这就是 DAG 调度必须做循环检测的原因。

---

## 06. 如何把示例扩展成真正的构建系统

上面的示例只解决了“顺序正确”。要变成真正可用的构建器，还需要补上这些能力：

| 能力 | 最小实现 | 进阶实现 |
|---|---|---|
| 增量构建 | 比较输入输出时间戳 | 基于内容哈希生成动作指纹 |
| 命令执行 | `subprocess.run()` | 日志分流、超时、失败恢复 |
| 并行调度 | 线程池 + 入度队列 | 资源感知调度、远程执行 |
| 缓存 | 本地 key-value 目录 | 远程缓存、CAS 内容寻址 |
| 依赖发现 | 手动声明依赖 | 编译器依赖文件、沙箱追踪 |
| 可复现性 | 固定命令和输入 | 锁定工具链、环境隔离、路径归一 |

其中并行调度可以从“入度队列”开始：

```text
1. 统计每个节点还有多少依赖未完成
2. 把依赖数为 0 的节点放入 ready queue
3. worker 从 ready queue 取任务执行
4. 任务完成后，减少后继节点的未完成依赖数
5. 新变成 0 的节点继续进入 ready queue
```

这就是很多构建系统、任务调度器和工作流引擎的共同底层模型。

---

## 07. 关键工程原则

构建系统越大，越需要遵守这些原则：

- <mark style="background:#10384a;color:#67e8f9;">显式依赖</mark>：规则应该清楚声明自己读取什么、生成什么。
- <mark style="background:#12351f;color:#86efac;">确定性输出</mark>：相同输入、相同规则、相同环境应得到相同产物。
- <mark style="background:#321936;color:#f0abfc;">可解释缓存</mark>：缓存命中或失效必须能解释原因。
- <mark style="background:#3a2b12;color:#facc15;">隔离副作用</mark>：规则不应该偷偷读取未声明文件、当前时间、随机数或网络状态。
- <mark style="background:#1e1b4b;color:#a5b4fc;">图优先思维</mark>：先建模依赖关系，再考虑命令怎么执行。

构建系统最怕的是“看起来能跑，但不知道为什么能跑”。一旦依赖不完整、缓存不透明、环境不固定，构建就会变成偶发失败和线上风险的来源。

---

## 08. 一句话总结

<div style="background:#070b14;color:#d8e7ff;border:1px solid #1e3a5f;border-radius:8px;padding:16px;">

构建系统的核心是：用 <mark style="background:#12351f;color:#86efac;">依赖图</mark> 表达目标之间的关系，用 <mark style="background:#10384a;color:#67e8f9;">拓扑排序</mark> 保证执行顺序，用 <mark style="background:#321936;color:#f0abfc;">时间戳或哈希</mark> 判断增量重建，用 <mark style="background:#3a2b12;color:#facc15;">调度器</mark> 把可并行的任务安全地跑起来。

</div>
