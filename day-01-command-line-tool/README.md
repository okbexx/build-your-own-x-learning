---
day: 1
topic: Command-Line Tool
status: done
source_repo: https://github.com/codecrafters-io/build-your-own-x
image_path: ~/build-your-own-x-learning/day-01-command-line-tool/learning-card.png
---

# Day 1 · Command-Line Tool

## 这是什么

命令行工具是通过终端输入命令与参数来完成任务的软件接口。它不依赖图形界面，而是把功能暴露成可组合、可脚本化、可自动化的文本接口。

## 怎么使用

典型使用方式是：

1. 在 shell 中输入命令名。
2. 附带参数、选项或子命令。
3. 从标准输出读取结果，或把结果通过管道交给下一个程序。

例如：

```bash
git status
curl https://example.com | jq .
ffmpeg -i in.mp4 out.gif
```

## 核心原理

命令行工具的本质，是把一个能力封装成“进程 + 参数 + 输入输出流”的协议：

- **参数解析**：把用户输入解析成结构化意图。
- **标准输入/输出/错误输出**：与外部环境交换数据。
- **退出码**：告诉调用方是否执行成功。
- **可组合性**：通过管道、重定向、脚本把多个小工具串起来。

所以 CLI 的核心思想不是“黑窗口”，而是：**把复杂能力压缩成可调用、可组合、可自动化的最小接口单位**。

## 适用场景

- 开发者工具
- 自动化脚本与运维任务
- 数据处理流水线
- AI Agent / 工作流编排
- 远程服务器操作

## 不适用边界

- 强依赖图形交互的场景
- 需要连续可视化编辑的场景
- 面向完全不懂命令的普通大众产品

## 为什么它重要

几乎所有现代开发基础设施最终都会暴露 CLI：编译器、包管理器、容器工具、部署工具、AI 编码代理。理解 CLI，本质上是在理解“软件能力如何被系统化调用”。

## 建议延伸

- 从 build-your-own-x 中任选一个 CLI 教程，优先看 Go / Rust / Node.js 版本。
- 动手做一个最小工具：比如 `todo`、`rename`、`fetch-json`。
- 观察你常用工具（git、docker、uv、ffmpeg）有哪些共同接口设计。
