# build-your-own-x-learning

这是一个围绕 [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) 展开的每日学习仓库。

目标不是简单收藏链接，而是按天沉淀一套可连续推进的学习产物：

- 每天一个主题
- 每个主题一个独立目录
- 每天至少包含：
  - `README.md`：中文原理理解版学习笔记
  - `learning-card.png`：中文深色科技风学习卡
- 用 `progress.md` 跟踪整体进度

## 进度总览

| Day | Topic | Status | Directory |
|---|---|---|---|
| 01 | Command-Line Tool | done | `day-01-command-line-tool/` |
| 02 | Shell | done | `day-02-shell/` |
| 03 | Text Editor | done | `day-03-text-editor/` |
| 04 | Git | done | `day-04-git/` |
| 05 | Database | done | `day-05-database/` |
| 06 | Search Engine | done | `day-06-search-engine/` |
| 07 | Web Server | done | `day-07-web-server/` |
| 08 | Web Browser | done | `day-08-web-browser/` |
| 09 | Network Stack | done | `day-09-network-stack/` |
| 10 | BitTorrent Client | done | `day-10-bittorrent-client/` |
| 11 | Docker | done | `day-11-docker/` |
| 12 | Blockchain / Distributed Ledger | done | `day-12-blockchain/` |
| 13 | Neural Network | done | `day-13-neural-network/` |
| 14 | AI Model | done | `day-14-ai-model/` |
| 15 | Operating System | done | `day-15-operating-system/` |
| 16 | Programming Language | done | `day-16-programming-language/` |
| 17 | Regex Engine | done | `day-17-regex-engine/` |
| 18 | Emulator / Virtual Machine | done | `day-18-emulator-vm/` |
| 19 | 3D Renderer | done | `day-19-3d-renderer/` |
| 20 | Game | done | `day-20-game/` |
| 21 | Bot | done | `day-21-bot/` |
| 22 | Frontend Framework / Library | done | `day-22-frontend-framework/` |
| 23 | Physics Engine | done | `day-23-physics-engine/` |
| 24 | Authentication / Login | done | `day-24-authentication/` |
| 25 | Template Engine | done | `day-25-template-engine/` |
| 26 | Build System | done | `day-26-build-system/` |
| 27 | Messaging Queue | done | `day-27-messaging-queue/` |
| 28 | Reactive System | planned | `day-28-reactive-system/` |
| 29 | Search / Recommendation Extension | planned | `day-29-search-recommendation/` |
| 30 | 自选综合主题 | planned | `day-30-capstone/` |

## 仓库结构

```text
build-your-own-x-learning/
├── README.md
├── progress.md
├── day-01-command-line-tool/
│   ├── README.md
│   └── learning-card.png
├── day-02-shell/
│   ├── README.md
│   └── learning-card.png
├── day-03-text-editor/
│   ├── README.md
│   └── learning-card.png
├── day-04-git/
│   ├── README.md
│   └── learning-card.png
└── day-05-database/
    ├── README.md
    └── learning-card.png
```

## 每日产物规范

### 1. README.md
每个 Day 的 `README.md` 采用中文“原理理解卡”结构，固定包含：

- 这是什么
- 怎么使用
- 核心原理
- 适用场景
- 不适用边界
- 为什么重要
- 建议延伸
- 对应的 build-your-own-x 原始项目地址

目标是：**看完就能快速建立对该主题的整体理解，而不是只停留在术语层面。**

### 2. learning-card.png
每个 Day 配套一张图片卡片，用来快速浏览该主题的重点。

要求：

- 中文
- 深色科技风
- 高信息密度
- 偏“原理理解卡”，不是社媒封面
- 必须是当日主题专属图片，不能复用前一天图片

## 进度管理

根目录的 `progress.md` 用来记录 30 天学习计划的推进状态。

状态说明：

- `planned`：未开始
- `done`：已完成
- `skipped`：跳过

当前已经完成：

- Day 01 · Command-Line Tool
- Day 02 · Shell
- Day 03 · Text Editor
- Day 04 · Git
- Day 05 · Database
- Day 06 · Search Engine
- Day 07 · Web Server
- Day 08 · Web Browser
- Day 09 · Network Stack
- Day 10 · BitTorrent Client
- Day 11 · Docker
- Day 12 · Blockchain / Distributed Ledger
- Day 13 · Neural Network
- Day 14 · AI Model
- Day 15 · Operating System
- Day 16 · Programming Language
- Day 17 · Regex Engine
- Day 18 · Emulator / Virtual Machine
- Day 19 · 3D Renderer
- Day 20 · Game
- Day 21 · Bot
- Day 22 · Frontend Framework / Library
- Day 23 · Physics Engine
- Day 24 · Authentication / Login
- Day 25 · Template Engine
- Day 26 · Build System
- Day 27 · Messaging Queue

## 如何继续生成下一天

如果要继续推进下一天内容，建议按下面流程执行：

1. 打开 `progress.md`，找到第一个 `planned` 的主题
2. 创建对应目录，例如 `day-06-search-engine/`
3. 先从 `build-your-own-x` 仓库中找到该主题对应的原始项目地址，并把链接写入当天的 `README.md`
4. 生成该 Day 的：
   - `README.md`
   - `learning-card.png`
5. 校验：
   - `README.md` 存在且非空
   - `README.md` 中包含对应的 build-your-own-x 原始项目地址
   - `learning-card.png` 存在且非空
   - 与前一天图片哈希不同，确保不是复用图
6. 更新 `progress.md`
7. 提交并推送到 GitHub

## 自动化约定

当前学习流转遵循这些规则：

- 每日主题产物统一落在本仓库中
- 计划按 Day 目录推进
- 定时任务执行时要求**显式调用 Codex CLI**
- 每天的学习内容必须贴出对应的 build-your-own-x 原始项目地址
- 只有在 `README.md` 与 `learning-card.png` 都生成并校验通过后，才更新 `progress.md`
- 不把每日学习过程自动写入 `all_in_one`
- 只有在用户自己形成总结并明确要求时，才再同步进知识库

## 仓库定位

这个仓库更像是一个**过程型学习仓库**，不是最终知识库本体。

它适合承载：

- 每日学习推进
- 原理理解卡片
- 阶段性学习痕迹
- 面向长期积累的主题目录结构

而更稳定、经过用户总结确认后的内容，才会视情况进入知识库体系。
