---
title: "Day 25｜Template Engine（模板引擎）学习笔记"
day: 25
topic: "Template Engine（模板引擎）"
status: done
date: "2026-05-16"
---

# Day 25｜Template Engine（模板引擎）

> `build-your-own-x / Day 25`
>
> 在模板引擎里，最值得学的不是“怎么写一段模板语法”，而是“如何把一段带占位符的文本，变成一个可执行、可扩展、可调试的渲染系统”。

---

## 01. 先建立心智模型

模板引擎的输入通常有两部分：

- 模板源码：一段带占位符、控制结构或组件标记的文本
- 运行上下文：一份对象、字典或响应式状态

输出则有三种典型形态：

- 最终字符串：例如 HTML、邮件、配置文件、SQL、代码生成结果
- 可执行渲染函数：先编译，后执行
- 虚拟 DOM 树：交给框架继续做差分和真实 DOM 更新

可以把它看成一条暗色编译管线：

```text
模板源码
  -> Token 化
  -> AST 构建
  -> 编译/解释
  -> 渲染输出（字符串 / 渲染函数 / VNode）
```

核心问题始终只有一个：

> 如何把“结构化模板”稳定地映射为“结构化输出”。

---

## 02. 模板引擎的核心原理

## 2.1 文本替换：最轻，最直观

最简单的模板引擎只做一件事：扫描文本，遇到 `{{name}}` 就从上下文里取 `name` 的值并替换。

```text
Hello, {{name}}!
```

如果上下文是：

```json
{ "name": "Ada" }
```

输出就是：

```text
Hello, Ada!
```

这一类引擎的特点：

- 实现成本最低
- 适合邮件模板、配置文件生成、简单代码生成
- 很难优雅支持 `if`、`for`、模板继承、作用域嵌套
- 一旦语法稍复杂，纯字符串替换会迅速失控

它更像“增强版查找替换”，不是完整编译器。

## 2.2 AST 编译：真正进入“语言实现”

当模板里出现条件分支、循环、局部变量、包含关系时，单纯替换已经不够了。此时就需要：

1. 先把模板切成 Token
2. 再把 Token 组织成 AST
3. 最后解释执行 AST，或者把 AST 编译成目标语言函数

例如：

```handlebars
{{#if user}}
  Hello, {{user.name}}
{{/if}}
```

它不再是“看到什么替换什么”，而是“先理解结构，再决定如何输出”。

这一类引擎的特点：

- 能表达完整控制流
- 易做缓存、调试、错误定位、预编译
- 适合服务端 HTML、静态站点生成、代码生成器
- 工程复杂度显著上升，但扩展性会好很多

这是大多数主流模板引擎真正的技术核心。

## 2.3 虚拟 DOM：模板不是直接产出字符串，而是产出界面树

在 Vue 这类前端框架中，模板常常不会直接变成字符串，而是先被编译为渲染函数，再返回虚拟 DOM 节点树。

```text
模板
  -> 编译器
  -> render()
  -> VNode Tree
  -> diff
  -> 真实 DOM 更新
```

这里的重点不再是“字符串拼接”，而是：

- 模板描述界面结构
- 编译器做静态分析和优化
- 运行时只更新变化部分

所以虚拟 DOM 路线本质上是“模板引擎 + 编译优化 + UI 运行时”的组合体。  
它比传统文本模板引擎更重，但也更强。

## 2.4 三条路线的本质差异

| 路线 | 输出目标 | 优势 | 代价 | 适用场景 |
| --- | --- | --- | --- | --- |
| 文本替换 | 纯字符串 | 实现极简，上手快 | 难支撑复杂语义 | 邮件、配置、简单生成 |
| AST 编译 | 字符串或函数 | 结构清晰，易扩展 | 需要解析器与执行器 | 服务端模板、静态生成 |
| 虚拟 DOM | VNode / render 函数 | 可静态优化，可增量更新 | 编译链更长，运行时更复杂 | 组件化前端框架 |

---

## 03. 关键数据结构与算法

## 3.1 Token 化：把连续字符流切成可理解单元

最小模板语法通常至少有三类片段：

- 纯文本：`TEXT`
- 插值表达式：`{{name}}`
- 控制块：`{{#if cond}} ... {{/if}}`

一个简化版 Token 结构可以这样设计：

```ts
type Token =
  | { type: "TEXT"; value: string }
  | { type: "VAR"; path: string[] }
  | { type: "BLOCK_START"; name: "if" | "each"; expr: string }
  | { type: "BLOCK_END"; name: "if" | "each" }
```

Token 化算法的关键点：

- 线性扫描字符串
- 识别分隔符 `{{` 与 `}}`
- 区分普通变量、块开始、块结束
- 保留原始位置信息，便于报错

如果模板长度为 `n`，一个良好的扫描器通常应做到 `O(n)`。

## 3.2 AST 构建：把线性 Token 流变成层级结构

Token 是平的，但模板的控制结构是嵌套的，因此需要 AST。

一个最小 AST：

```ts
type Node =
  | { type: "Root"; children: Node[] }
  | { type: "Text"; value: string }
  | { type: "Variable"; path: string[] }
  | { type: "If"; expr: string; children: Node[] }
  | { type: "Each"; expr: string; children: Node[] }
```

例如：

```handlebars
Hello {{name}}
{{#if admin}}
  [root]
{{/if}}
```

会被组织成：

```text
Root
├─ Text("Hello ")
├─ Variable(["name"])
└─ If("admin")
   └─ Text("[root]")
```

常见构建方式有两种：

- 递归下降：语法简单时最容易读懂
- 栈式归约：遇到块开始压栈，遇到块结束出栈

对模板引擎来说，栈式构建通常非常够用。

## 3.3 上下文渲染栈：处理作用域、循环变量与回退查找

模板引擎不只是在一个对象里查值。只要出现循环、局部上下文、包含模板，作用域就会变化。

因此需要一个“上下文栈”：

```ts
type Frame = Record<string, unknown>
type ContextStack = Frame[]
```

查找变量 `user.name` 时，通常从栈顶往下找：

1. 先查当前局部作用域
2. 找不到再查父作用域
3. 找到对象后按路径逐层取值

这能解决几个关键问题：

- `each` 内部的当前项遮蔽外层变量
- 局部变量不会污染全局
- 模板嵌套时仍能稳定回退

这是模板引擎从“字符串替换器”升级为“可执行作用域系统”的关键一步。

## 3.4 渲染算法：深度优先遍历 AST

最常见的执行方式是 DFS：

- `Text`：直接写入输出缓冲区
- `Variable`：解析路径，取值，转义，再写入
- `If`：计算条件，为真则渲染子节点
- `Each`：迭代集合，为每一项压入新作用域并渲染子节点

输出缓冲区可以是：

- 字符串数组：最后 `join("")`
- 可写流：适合大模板和流式输出

在工程实现里，字符串数组通常是最稳妥的起点。

---

## 04. 从 0 到 1：最小可运行实现思路

如果目标是“先做出能跑的最小模板引擎”，建议只支持这三种语法：

- 变量插值：`{{name}}`
- 条件块：`{{#if cond}} ... {{/if}}`
- 列表块：`{{#each items}} ... {{/each}}`

不要一开始就做：

- 模板继承
- 过滤器
- 宏
- 异步渲染
- 自定义语法扩展

先把主干打通，再谈高级能力。

## 4.1 最小架构

```text
compile(template):
  tokens = tokenize(template)
  ast = parse(tokens)
  return function render(context):
    return execute(ast, context)
```

这个 `compile` 思路很重要，因为它把“解析成本”与“渲染成本”分离了：

- 模板可预编译并缓存
- 同一模板可被多次复用
- 错误可在编译阶段尽早暴露

## 4.2 伪代码：Token 化

```text
function tokenize(input):
  i = 0
  tokens = []

  while i < input.length:
    if startsWith(input, i, "{{"):
      j = findClosing(input, i + 2, "}}")
      raw = trim(input[i + 2 : j])

      if raw startsWith "#if ":
        tokens.push(BLOCK_START("if", raw after "#if "))
      else if raw startsWith "#each ":
        tokens.push(BLOCK_START("each", raw after "#each "))
      else if raw startsWith "/if":
        tokens.push(BLOCK_END("if"))
      else if raw startsWith "/each":
        tokens.push(BLOCK_END("each"))
      else:
        tokens.push(VAR(splitPath(raw)))

      i = j + 2
    else:
      j = findNextOpen(input, i, "{{")
      tokens.push(TEXT(input[i : j]))
      i = j

  return tokens
```

## 4.3 伪代码：AST 构建

```text
function parse(tokens):
  root = Root([])
  stack = [root]

  for token in tokens:
    current = top(stack)

    if token.type == TEXT:
      current.children.push(Text(token.value))

    else if token.type == VAR:
      current.children.push(Variable(token.path))

    else if token.type == BLOCK_START and token.name == "if":
      node = If(token.expr, [])
      current.children.push(node)
      stack.push(node)

    else if token.type == BLOCK_START and token.name == "each":
      node = Each(token.expr, [])
      current.children.push(node)
      stack.push(node)

    else if token.type == BLOCK_END:
      assert top(stack).type matches token.name
      stack.pop()

  assert stack.length == 1
  return root
```

## 4.4 伪代码：渲染执行

```text
function renderNode(node, ctxStack, out):
  if node.type == Text:
    out.push(node.value)

  else if node.type == Variable:
    value = resolve(node.path, ctxStack)
    out.push(escapeHtml(stringify(value)))

  else if node.type == If:
    if truthy(resolveExpr(node.expr, ctxStack)):
      for child in node.children:
        renderNode(child, ctxStack, out)

  else if node.type == Each:
    items = resolveExpr(node.expr, ctxStack)
    for item in items:
      ctxStack.push({ this: item, ...item })
      for child in node.children:
        renderNode(child, ctxStack, out)
      ctxStack.pop()

function execute(ast, context):
  out = []
  ctxStack = [context]

  for child in ast.children:
    renderNode(child, ctxStack, out)

  return join(out, "")
```

## 4.5 一个最小例子

模板：

```handlebars
<ul>
{{#each users}}
  <li>{{name}}</li>
{{/each}}
</ul>
```

上下文：

```json
{
  "users": [
    { "name": "Ada" },
    { "name": "Linus" }
  ]
}
```

输出：

```html
<ul>
  <li>Ada</li>
  <li>Linus</li>
</ul>
```

如果这一步能稳定跑通，说明你的引擎已经完成了最核心的骨架。

---

## 05. 构建时最容易踩的坑

- HTML 转义：`{{name}}` 默认是否转义，决定了安全边界
- 空值语义：变量不存在时返回空串、报错，还是保留原样
- 空白控制：模板换行和缩进是否应进入最终输出
- 错误定位：缺少闭合标签时，要能报到模板行列号
- 作用域遮蔽：循环体内变量名与外层同名时如何解析
- 缓存策略：模板是否按源码或文件路径缓存编译结果
- 扩展边界：过滤器、辅助函数、包含、继承会迅速放大复杂度

模板引擎的难点往往不在“能不能渲染出来”，而在“复杂度增长后还能不能保持规则清晰”。

---

## 06. 与主流引擎对比

| 引擎 | 本质路线 | 典型输出 | 强项 | 代价与边界 |
| --- | --- | --- | --- | --- |
| Jinja2 | AST 编译，接近服务端模板语言 | HTML / 任意文本 | 模板继承、过滤器、宏、缓存、沙箱能力强 | 偏服务端语境，模板语言本身已较丰富 |
| EJS | 模板转 JavaScript 函数 | HTML / 文本 | 思维直接，和 JS 结合紧密，灵活度高 | 容易把业务逻辑塞进模板，约束较弱 |
| Handlebars | 受限表达式 + AST / 预编译 | HTML / 文本 | 逻辑克制、语义清晰、适合多人协作 | 表达力弱于 EJS，需要 helper 扩展 |
| Vue SFC | 模板编译为 render 函数，再生成 VNode | 虚拟 DOM / 真实 UI | 静态分析优化、组件化、响应式联动 | 它已不只是模板引擎，而是完整前端编译链 |

### 6.1 Jinja2

Jinja2 更像“模板语言系统”而非简单模板器。

它适合学习的点：

- 模板如何编译并缓存
- 模板继承如何形成多层结构
- 沙箱与转义如何进入设计核心

如果你想做的是服务端页面渲染或代码生成器，Jinja2 的设计非常值得拆。

### 6.2 EJS

EJS 的路线是把模板嵌入 JavaScript 语境，然后生成函数执行。

它适合学习的点：

- 模板如何降级为字符串拼接代码
- 为什么“灵活”往往意味着“边界容易失控”

EJS 很适合理解“模板编译到宿主语言函数”这件事。

### 6.3 Handlebars

Handlebars 强调“限制模板表达力”，把复杂逻辑外推到 helper。

它适合学习的点：

- 如何用受限语法换来可维护性
- 如何做预编译、局部模板、helper 机制

如果你想做一个团队可控、可读性高的模板系统，它是很好的参考对象。

### 6.4 Vue SFC

Vue SFC 的模板部分已经进入“编译器工程”层级。

它适合学习的点：

- 模板如何编译成渲染函数
- 编译期如何识别静态节点、指令和依赖
- 为什么虚拟 DOM 路线要求模板具备更强的静态可分析性

它提醒我们：模板引擎的终点不一定是字符串，也可以是高性能 UI 更新系统。

---

## 07. 推荐的从零实现路线

建议按下面顺序推进，而不是一口气做大：

1. 只支持 `{{var}}`
2. 加入 `if`
3. 加入 `each`
4. 引入上下文栈
5. 增加 HTML 转义
6. 做编译缓存
7. 加错误位置信息
8. 再考虑 partial / include
9. 最后再碰继承、宏、异步、沙箱

这个顺序的价值在于：

- 每一步都能独立验证
- 每一步都能暴露设计缺口
- 不会太早陷入高级特性泥潭

从学习角度说，模板引擎最值得掌握的不是语法表面，而是这条演进链：

> 文本替换器  
> -> 结构化解析器  
> -> 带作用域的执行器  
> -> 可缓存、可调试、可扩展的编译系统

---

## 08. 学完这一题应该真正带走什么

如果只记一个结论，我会记这个：

> 模板引擎本质上是一门“小语言”的实现。

它至少包含：

- 词法分析
- 语法结构
- 作用域模型
- 执行语义
- 安全策略
- 编译与缓存

所以做模板引擎，不是在练字符串技巧，而是在练一整套“微型编译器”思维。  
一旦你把这套思路吃透，再去看 Jinja2、Handlebars、Vue 编译器，很多设计都会自然对上。

---

## 09. 延伸学习资源

- Build Your Own X：<https://github.com/codecrafters-io/build-your-own-x>
- Jinja 官方文档：<https://jinja.palletsprojects.com/en/stable/>
- Jinja 模板设计文档：<https://jinja.palletsprojects.com/en/2.10.x/templates/>
- EJS 官方文档：<https://ejs.co/>
- Handlebars 指南：<https://handlebarsjs.com/guide/>
- Handlebars 表达式文档：<https://handlebarsjs.com/guide/expressions>
- Vue 单文件组件语法定义：<https://cn.vuejs.org/api/sfc-spec>
- Vue 渲染机制：<https://vuejs.org/guide/extras/rendering-mechanism>
- Crafting Interpreters：<https://craftinginterpreters.com/>

---

## 10. 复盘问题

读完后，可以反问自己：

1. 为什么复杂模板引擎几乎都会走向 AST，而不是继续做字符串替换？
2. 为什么上下文栈是模板引擎里非常关键但又很容易被低估的设计？
3. Vue 模板和 Jinja2 模板的“输出目标”差异，为什么会导致完全不同的编译策略？
4. 如果让我自己做一个最小模板引擎，第一版我会故意不做哪些功能？

能把这四个问题答清楚，这一题就不只是“看过”，而是真正理解了。
