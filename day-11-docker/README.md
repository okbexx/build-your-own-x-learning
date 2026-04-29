---
day: 11
topic: Docker
status: done
source_repo: https://github.com/codecrafters-io/build-your-own-x
image_path: ~/build-your-own-x-learning/day-11-docker/learning-card.png
---

# Day 11 · Docker

本日目标：用“自己动手实现一个简化版 Docker”的视角，建立一套能落地的心智模型——Docker 到底解决了什么问题、它为何能“像进程一样启动应用却像虚拟机一样隔离”、以及镜像/容器背后的关键内核机制是什么。你不需要把所有实现细节都背下来，但要能解释：**容器并不是虚拟机；容器本质上是“被隔离与被限制的一组进程 + 一个分层文件系统视图 + 一套运行时约束”**。

---

# build-your-own-x 对应原始项目地址

对应 build-your-own-x 仓库的条目（精确锚点链接）：

- https://github.com/codecrafters-io/build-your-own-x#build-your-own-docker

---

# 这是什么

这里的 “Docker” 学习不是教你背命令，而是把 Docker 拆成几个可以解释、可以复现的组成部分：

1. **镜像（Image）**：一种可分发、可复用的“文件系统快照 + 元数据（入口命令、环境变量、默认工作目录等）”，并且以“分层（layer）”的方式存储与复用。
2. **容器（Container）**：镜像的一个运行实例。它看起来像一台“迷你机器”，但从 Linux 内核视角，它就是一组普通进程，只是：
   - 看到的资源视图被隔离（namespace）
   - 使用资源的额度被限制/计量（cgroups）
   - 文件系统视图是“只读层 + 可写层”的联合挂载（UnionFS/overlayfs）
3. **容器运行时（Runtime）**：把“镜像”变成“进程”的那段胶水：准备 rootfs、设置隔离与限制、配置网络/挂载、最后 `exec` 你的入口进程。现实世界里通常是 OCI 生态（如 runc/containerd）。

当你能把 Docker 拆成这三件事，并能解释它们如何协作，你就真正“会 Docker”了——不仅会用，而且能排障、能设计部署方案、能理解安全边界。

---

# 怎么使用

下面以“从常用到原理”的顺序，给出一套建议的使用方式（你不需要现在就执行，重点是理解每一步对应的底层含义）。

## 1) 用镜像启动容器（从“分发”到“运行”）

- 拉取镜像：`docker pull <image>:<tag>`
  - 含义：把镜像的各个 layer 下载到本机的镜像存储中；同一个 layer 可被多个镜像共享（内容寻址）。
- 启动容器：`docker run --rm -it <image>:<tag> <cmd>`
  - 含义：为该镜像创建一个容器实例（包含一层可写层），设置 namespace/cgroups 等隔离与限制，然后把 `<cmd>` 作为容器内的 PID 1 进程启动。

## 2) 用 Dockerfile 构建镜像（从“过程”到“分层快照”）

- 构建：`docker build -t myapp:dev .`
  - 含义：Dockerfile 的每条指令往往会形成一个新的 layer（具体取决于构建器与优化策略），并把结果缓存起来，以便下次只重建变化部分。

理解构建的关键在于：**镜像不是“一个大 tar 包”，而是一组可复用的层**。这使得分发快、缓存命中高、CI/CD 构建效率显著提升。

## 3) 观测与调试（把“容器黑盒”变成“可解释对象”）

- 查看进程：`docker top <container>`
  - 含义：容器内的进程在宿主机上仍是普通进程，只是处在不同的 namespace 中。
- 查看资源限制：`docker inspect <container>` / `docker stats`
  - 含义：对应 cgroups 的限制与统计信息（CPU、内存、IO、pids 等）。
- 进入容器：`docker exec -it <container> sh`
  - 含义：在同一套 namespace/cgroups/rootfs 约束中再启动一个新进程，而不是“登录另一台机器”。

## 4) 最小可用的“手工容器”思路（帮助你把原理连起来）

当你实现/理解“自己动手 Docker”时，可以把流程简化成：

1. 准备 rootfs（解压一个 root filesystem，或基于镜像 layer 组装一个 overlay）
2. `clone()`/`unshare()` 创建并进入新的 namespace（pid/mount/net/uts/ipc/user 等）
3. 配置 cgroups（写入 cgroupfs 或通过 systemd 接口）
4. 设置 mount（挂载 proc、dev、overlayfs、bind mount 等）
5. `chroot`/`pivot_root` 切换根目录
6. 最后 `execve()` 执行入口程序成为容器内 PID 1

你会发现：**Docker 的“魔法”几乎都来自 Linux 内核能力的组合，而不是 Docker 自己发明了一个新 OS。**

---

# 核心原理

这一节是本日最重要的内容。Docker 之所以能成立，是因为它把隔离（namespace）、限制（cgroups）和文件系统分层（overlayfs）组合在一起，再配合运行时（OCI runtime）把这些能力工程化、产品化。

## 1) Namespace：隔离“你看见的世界”

namespace 解决的问题是：**同一台宿主机上的不同进程组，看到的“系统视图”可以不同**。这不是安全的全部，但它是“看起来像一台独立机器”的根基。

常见 namespace 及其作用：

- **PID namespace**：隔离进程号空间。
  - 容器内会有自己的 PID 1。这个 PID 1 不是宿主机真正的 1 号进程，但在容器内它承担 init 的角色（比如接收信号、回收僵尸进程）。
  - 这也是为什么很多容器需要一个合适的 init 或正确处理信号/僵尸进程，否则会出现“优雅退出失败”或僵尸堆积。
- **Mount namespace**：隔离挂载点视图。
  - 容器可以有自己的一套挂载表（mount table），你在容器里挂载/卸载不会影响宿主机或其他容器（前提是挂载传播属性配置正确）。
  - overlayfs/UnionFS 正是通过 mount namespace + 特定挂载方式为容器提供“分层文件系统视图”。
- **Network namespace**：隔离网络栈。
  - 容器内有独立的网卡（通常是 veth 设备的一端）、路由表、iptables 规则空间等。
  - Docker 默认用 bridge 网络把容器挂到一个 Linux bridge 上，再做 NAT/端口映射，实现“容器内私网 + 对外暴露端口”。
- **UTS namespace**：隔离主机名/域名（hostname/domainname）。
  - 让容器看起来有自己的 hostname。
- **IPC namespace**：隔离 System V IPC、POSIX message queues 等。
  - 避免跨容器的 IPC 资源互相干扰。
- **User namespace**：隔离用户与组 ID 映射（非常关键但常被忽略）。
  - 能把容器内的 root 映射到宿主机的非特权 UID，从而大幅降低容器逃逸后的危害面。
  - 现实中出于兼容性/运维复杂度，很多环境并未默认启用 userns，但从安全角度它很重要。

理解要点：namespace 主要是**隔离视图与命名空间**，让容器“像独立系统”；但**资源是否会被抢光**，是 cgroups 负责的；**文件系统如何呈现**，是 overlayfs/挂载负责的。

## 2) Cgroups：限制与计量“你能用多少资源”

cgroups（control groups）解决的问题是：**让内核对进程组进行资源配额、优先级控制和使用统计**。没有 cgroups，就算 namespace 让进程“看起来隔离”，它仍可能把 CPU 打满、把内存吃光、把 IO 打爆，影响整机稳定性。

关键能力（不同版本 cgroups v1/v2 细节不同，但核心思想一致）：

- **CPU**：限制 CPU 时间片占用、设置权重（shares/weight）、配额（quota/period）。
  - 适用于：防止某个容器把 CPU 吃满；或给关键服务更高权重。
- **Memory**：限制内存上限、触发回收、统计缓存/匿名页等。
  - 现实行为复杂：内存限制触发时可能导致 OOM kill（杀死进程），并且 OOM 的选择策略与容器内/宿主机视角有关，需要结合应用的内存模型理解。
- **IO（blkio / io controller）**：限制块设备 IO 带宽/IOPS，或设置权重。
  - 对数据库、日志写入密集型服务很关键。
- **PIDs**：限制可创建的进程数，防止 fork bomb 类问题。
- **Devices**：控制可访问的设备节点（配合 Linux capabilities、seccomp 等进一步缩小权限）。

理解要点：

- cgroups 是“资源管理”，不是“隔离视图”；它更像“配额与账本”。
- 容器编排（如 Kubernetes）之所以能做 QoS、requests/limits，本质上也是在驱动 cgroups。

## 3) UnionFS / overlayfs：把“只读层 + 可写层”组合成一个 rootfs

容器文件系统的关键目标是：**镜像可复用、容器可写、启动要快、占用要小**。为此 Docker 广泛使用分层文件系统（UnionFS 思想），在 Linux 上常见实现是 overlayfs。

overlayfs 的典型结构：

- **lowerdir**：一个或多个只读层（镜像 layers）。
- **upperdir**：容器的可写层（每个容器独有）。
- **workdir**：overlayfs 工作目录（内部需要）。
- **merged**：最终呈现给容器的合并视图（rootfs 视图）。

关键行为（理解后排障会容易很多）：

- **写时复制（Copy-on-Write, CoW）**：
  - 当容器第一次修改某个来自只读层的文件时，overlayfs 会把该文件“拷贝”到 upperdir，然后后续写入都发生在 upperdir。
  - 所以：同一个基础镜像启动多个容器，读共享、写分离；节省空间、提升启动速度。
- **白化（whiteout）与遮蔽（opaque）**：
  - 当上层需要“删除”下层文件时，不能真的改下层（只读），于是用 whiteout 标记在合并视图中隐藏它。
  - 这解释了某些场景下你在容器里删除文件，镜像层并不会变小；镜像层是不可变的，删除只是上层“遮住”。
- **性能与语义差异**：
  - overlayfs 对某些文件操作语义与真实 ext4/xfs 略有差异；大量小文件写入、元数据密集操作时，CoW 带来额外开销。
  - 这也是为什么数据库常建议把数据目录放到 volume（绑定到宿主机真实文件系统）而不是容器可写层。

## 4) 镜像分层：内容寻址、复用与缓存的工程化

镜像分层不是“为了炫技”，它直接带来工程收益：

- **分发加速**：客户端只需要下载缺失的层；公共基础层（如语言运行时）可被大量镜像共享。
- **构建缓存**：Dockerfile 的层可缓存，变更发生在哪一层就重建哪一层之后的内容。
- **不可变基础**：层不可变，利于回滚与可重复部署（同一 digest 对应同一内容）。

但也要理解分层的代价与陷阱：

- 层越多并不一定越好：会增加元数据管理开销，影响构建/加载速度。
- 不合理的 Dockerfile（比如频繁变更的内容放在靠前层）会导致缓存失效，构建变慢。
- 镜像分层是“文件系统层面”的增量，并不能自动优化应用层依赖（例如 node_modules 的构建策略仍需设计）。

## 5) 容器运行时：把“规范”落地为“可执行流程”

现实世界 Docker 体系可以粗略拆成三层：

- **Docker CLI / API**：用户界面与 REST API。
- **容器管理守护进程与编排组件**：负责镜像拉取、网络/存储配置、生命周期管理。
- **容器运行时（OCI runtime）**：最终负责在内核层面启动容器进程（典型是 runc）。

关键点在于：容器运行时做的事情，基本就是把“一个 OCI bundle（rootfs + config.json）”变成“一个在特定 namespace/cgroups 中运行的进程”。这一步包括：

- 设置 namespace（clone/unshare/setns 等）
- 设置 cgroups（写入 cgroupfs 或委托 systemd）
- 设置 capabilities、seccomp、apparmor/selinux（安全边界的重要组成）
- 配置 mount（proc、sysfs、devtmpfs、overlay、bind mounts）
- 切换 root（pivot_root/chroot）
- 最后 exec 入口程序

你实现“自己的 Docker”时，不必复制完整 OCI 生态，但要能把这些步骤串起来，并理解每一步是为了解决哪类问题。

---

# 适用场景

Docker（更广义的容器技术）适用于以下典型场景，背后的共同点是：**需要一致的运行环境 + 可控的资源使用 + 快速交付与回滚**。

1. **应用交付与环境一致性**
   - 解决“我本地能跑、线上不能跑”的依赖/系统库差异问题。
   - 镜像把用户态依赖固定下来，部署变成“运行同一个镜像”。
2. **微服务与弹性扩缩容**
   - 容器启动速度快、实例密度高，便于水平扩展。
   - 与编排系统结合（如 Kubernetes）可实现自动扩缩、滚动更新、健康检查。
3. **CI/CD 构建与测试隔离**
   - 每个任务在独立容器里运行，依赖冲突与污染显著减少。
   - 分层缓存可加速构建。
4. **多租户/多任务的资源治理**
   - cgroups 让同机部署的服务不会轻易互相“拖垮”。
5. **可复现的开发环境**
   - 结合 devcontainer、docker-compose 等，让团队成员拿到一致工具链与依赖。

---

# 不适用边界

理解“不适用”比理解“适用”更能体现对边界的把握。Docker 并不是银弹，以下情况要谨慎：

1. **把容器当作强安全边界**
   - 容器共享宿主机内核，隔离强度通常低于虚拟机；如果你需要强隔离（例如不可信代码执行），应优先考虑更强的沙箱或 VM（或至少启用 userns、seccomp、SELinux/AppArmor 等强化）。
2. **极端 I/O 密集且依赖稳定低延迟的工作负载**
   - overlayfs 的 CoW 和元数据开销会影响性能；数据库/消息队列的数据目录通常应该放到 volume 或裸盘/直挂文件系统。
3. **强依赖特定内核特性/驱动的场景**
   - 例如需要直接操作某些硬件设备、内核模块、特权操作。虽然可以用 `--privileged` 或设备映射，但这会显著扩大攻击面，削弱容器隔离的意义。
4. **“把所有东西都塞进一个大容器”当作部署架构**
   - 容器本质是进程模型，过度在一个容器里堆叠多个服务会让日志、健康检查、生命周期、资源治理复杂化；更常见是“一容器一进程（或一主进程）”的思路。

---

# 为什么它重要

Docker 重要的不只是“好用”，而是它在工程层面统一了交付与运行的抽象：

1. **把“环境”变成可版本化的产物**
   - 过去环境靠文档与口口相传；现在镜像把依赖变成可追踪、可回滚、可审计的构件。
2. **把“进程”提升为“可治理的部署单元”**
   - 通过 namespace/cgroups，进程不再只是 OS 里的一个 PID，而是拥有隔离视图、资源边界、可观测指标的单位。
3. **提升交付速度与密度**
   - 秒级启动、层复用、缓存构建，让从开发到上线的循环变短；同机可承载更多实例，提升资源利用率。
4. **为云原生生态打地基**
   - Kubernetes、服务网格、镜像仓库、供应链安全（SBOM、签名）等能力都围绕“镜像/容器”展开。
5. **让你在排障与安全上更专业**
   - 当你理解 namespace/cgroups/overlayfs/运行时，就能解释：为什么容器里看不到某些进程、为什么内存限制触发 OOM、为什么删除文件镜像不变小、为什么某些权限被拒绝。

---

# 建议延伸

如果你想把本日知识从“会讲”变成“会做”，可以按以下路线深入（建议从前到后，循序渐进）：

1. **亲手实现最小容器运行器**
   - 用 `unshare`/`clone` + `pivot_root` + 挂载 `/proc` 做出“有自己 PID 1、能跑 shell”的最小容器。
2. **补齐 cgroups v2 的理解**
   - 理解 unified hierarchy、cpu.max、memory.max、io.max 等接口；学会从限制与统计角度读懂性能问题。
3. **深入 overlayfs 与镜像层的真实行为**
   - 重点理解：CoW、whiteout、opaque 目录，以及为什么 volume 能解决写放大与性能问题。
4. **了解 OCI 生态与 containerd/runc 的分工**
   - 把“Docker 是一个产品”拆成“OCI 规范 + runtime + 管理守护进程 + 镜像分发”，形成可迁移的知识（面对不同发行版/云厂商也不慌）。
5. **安全强化实践**
   - 学习并实践：最小权限（capabilities）、seccomp profile、AppArmor/SELinux、rootless 容器、user namespace 映射。
6. **从 Docker 过渡到编排**
   - 学习 docker-compose 的服务编排思路，再到 Kubernetes 的 Pod/Deployment/Service，理解“容器只是最小执行单元，真正的生产能力来自编排与治理”。

