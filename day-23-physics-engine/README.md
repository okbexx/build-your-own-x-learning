---
day: 23
topic: Physics Engine
status: done
date: 2026-05-14
---

# Day 23 · Physics Engine

> `SIMULATE MOTION // DETECT CONTACT // SOLVE CONSTRAINTS`
>
> 从零开始构建物理引擎，真正要学的不是“让方块掉下来”，而是理解：  
> 一个离散时间系统，怎样在**速度、位置、碰撞、约束、数值稳定性**之间维持可控平衡。

🌌🌌🌌

## 🌑 这是什么

“物理引擎”这个名字很容易让人误会，仿佛它是在完整模拟真实世界。实际上，游戏和交互系统中的物理引擎，通常不是做严格的科学仿真，而是在**实时性、稳定性、可玩性**三者之间取一个工程折中。

如果从实现角度拆开看，一个最小可用的物理引擎要回答四个问题：

| 问题 | 本质 | 典型输出 |
| --- | --- | --- |
| 物体会怎么动？ | 刚体动力学 + 数值积分 | 新的位置与姿态 |
| 物体碰到了什么？ | 碰撞检测 | 接触点、法线、穿透深度 |
| 碰到之后怎么办？ | 冲量 / 约束求解 | 新的线速度、角速度 |
| 怎样保持稳定？ | 固定时间步长、迭代求解、误差修正 | 不穿模、不抖动、不爆能量 |

所以，自制物理引擎的核心不是“堆 API”，而是实现一条稳定的计算流水线：

```text
施加外力
  -> 积分预测速度
  -> 宽相位碰撞检测
  -> 窄相位求接触信息
  -> 约束 / 冲量迭代求解
  -> 积分位置与角度
  -> 睡眠 / 清理 / 进入下一帧
```

从学习顺序看，**2D 刚体物理**是最适合“从零实现”的入口。因为在 2D 中，旋转只有一个角度 `θ`，角速度 `ω` 是标量，转动惯量 `I` 也通常能先简化成标量，这会大幅降低数学和代码复杂度。理解了 2D，扩展到 3D 的核心思想并不会变，只是向量、矩阵、惯性张量和接触情况更复杂。

🌌🌌🌌

## 🧱 核心抽象：刚体到底保存什么

一个刚体不是一张图片，也不是一个“游戏对象”按钮。它是一个状态集合。

在 2D 中，最常见的状态是：

- 位置 `x`
- 朝向角 `θ`
- 线速度 `v`
- 角速度 `ω`
- 质量 `m` 与逆质量 `invMass`
- 转动惯量 `I` 与逆惯量 `invI`
- 累积外力 `F`
- 累积力矩 `τ`

可以把它写成这样：

```cpp
struct Body {
    Vec2 position;
    float angle;

    Vec2 velocity;
    float angularVelocity;

    Vec2 force;
    float torque;

    float mass;
    float invMass;

    float inertia;
    float invInertia;

    bool isStatic;
};
```

这里有一个很重要的工程技巧：**静态物体通常不是靠“无限大质量”表示，而是直接令 `invMass = 0`、`invInertia = 0`**。这样在公式里自然就不会被速度修正推动。

### 刚体动力学的最小公式

在连续时间里，牛顿-欧拉方程可以写成：

```text
线性运动:
m * dv/dt = ΣF
dx/dt = v

旋转运动:
I * dω/dt = Στ
dθ/dt = ω
```

整理后得到：

```text
a = ΣF / m
α = Στ / I
```

也就是说，物理引擎每一帧真正做的第一件事，不是直接改位置，而是：

1. 根据力求加速度
2. 根据加速度更新速度
3. 再根据速度更新位置

这听起来普通，但它决定了引擎的数值稳定性。

🌌🌌🌌

## ⚙️ 时间推进：为什么大家都强调固定时间步长

物理系统是连续的，而计算机是离散的。你必须选择一个 `dt`，用它把连续运动切成很多小步。

最常见建议有两个：

- 使用**固定时间步长**，例如 `1/60 s`
- 使用**半隐式欧拉积分**，而不是最直观的显式欧拉

### 显式欧拉 vs 半隐式欧拉

显式欧拉：

```text
x(t + dt) = x(t) + v(t) * dt
v(t + dt) = v(t) + a(t) * dt
```

半隐式欧拉：

```text
v(t + dt) = v(t) + a(t) * dt
x(t + dt) = x(t) + v(t + dt) * dt
```

半隐式欧拉看起来只调换了两行顺序，但对能量行为更友好，实际游戏物理里广泛使用。原因很朴素：你先更新速度，再用更新后的速度推进位置，会比“拿旧速度硬推”更稳定。

### 一个极简的世界步进框架

```cpp
void Step(World& world, float dt) {
    for (Body& b : world.bodies) {
        if (b.invMass == 0.0f) continue;

        Vec2 acceleration = world.gravity + b.force * b.invMass;
        float angularAcceleration = b.torque * b.invInertia;

        b.velocity += acceleration * dt;
        b.angularVelocity += angularAcceleration * dt;
    }

    DetectCollisions(world);
    SolveConstraints(world, dt);

    for (Body& b : world.bodies) {
        if (b.invMass == 0.0f) continue;

        b.position += b.velocity * dt;
        b.angle += b.angularVelocity * dt;

        b.force = Vec2(0, 0);
        b.torque = 0.0f;
    }
}
```

### 为什么不建议直接用可变 `dt`

因为同一套求解器，在 `dt = 1/120` 和 `dt = 1/20` 下的误差行为完全不同。  
时间步长一旦忽大忽小，接触、摩擦、弹性恢复、关节约束都会变得不可预测，最典型现象就是：

- 小物体抖动
- 物体堆叠发散
- 高速物体穿透
- 系统能量异常增长

所以很多引擎都采用固定物理步进，再让渲染自己插值显示。

🌌🌌🌌

## 🛰️ 碰撞检测：先找到“谁可能撞了”，再判断“到底撞没撞”

碰撞检测通常分两层：

| 层级 | 目标 | 常见算法 |
| --- | --- | --- |
| 宽相位 Broad Phase | 快速筛掉大多数不可能碰撞的对 | AABB、Sweep and Prune、Dynamic BVH |
| 窄相位 Narrow Phase | 精确计算是否接触、法线和穿透量 | Circle-Circle、SAT、GJK/EPA |

### 1. 宽相位：别让所有物体两两检测

如果场景里有 `n` 个物体，最原始做法是两两检测，复杂度约为 `O(n^2)`。一旦物体稍多，这会迅速失控。

所以宽相位的目标不是“精确碰撞”，而是先快速问一句：

> 这两个物体的包围盒，有没有可能重叠？

最简单的包围体是 AABB（轴对齐包围盒）：

```text
AABB = [minX, minY, maxX, maxY]
```

两个 AABB 是否重叠，只需比较区间：

```text
if a.maxX < b.minX or a.minX > b.maxX => 分离
if a.maxY < b.minY or a.minY > b.maxY => 分离
否则 => 可能接触
```

这一步非常便宜，因此适合每帧大量执行。

### 2. 窄相位：真正计算接触信息

#### 圆与圆

圆是最容易处理的形状。设两个圆心分别为 `pA`、`pB`，半径为 `rA`、`rB`，则：

```text
d = pB - pA
dist = |d|

若 dist < rA + rB，则发生重叠
接触法线 n = normalize(d)
穿透深度 penetration = rA + rB - dist
```

这一类检测的优点是公式短、结果稳定，非常适合作为第一步练手。

#### 多边形与多边形：SAT 分离轴定理

对于凸多边形，一个非常经典的思路是 SAT（Separating Axis Theorem）：

> 如果两个凸体不相交，那么一定存在一条轴，使得它们在这条轴上的投影区间分离。

实现步骤通常是：

1. 取两个多边形所有边的法线作为候选轴
2. 把两个多边形顶点分别投影到这条轴上
3. 比较两个投影区间是否重叠
4. 只要找到一条分离轴，就说明未碰撞
5. 如果所有轴都重叠，则碰撞，且重叠最小的轴常被用作接触法线候选

SAT 的难点不在“判定相交”，而在**稳定地产生接触法线和接触点**。真正的引擎还要继续做 clipping，生成 contact manifold（接触流形）。

#### GJK / EPA

如果想把引擎继续做深，可以研究：

- `GJK`：用于判断两个凸体是否相交
- `EPA`：在相交后继续求穿透深度和法线

它们非常经典，但对第一次手写物理引擎来说，不一定是最佳起点。学习顺序上，先把 SAT + 圆形跑通，通常更稳。

🌌🌌🌌

## 💥 碰撞响应：为什么不是“把位置推开”这么简单

很多新手实现碰撞时，第一反应是：既然重叠了，那我把两个物体直接分开不就行了？

这只能修正位置错误，却没有正确处理**动量交换**。物体会“被拉开”，但不会出现合理反弹、摩擦或旋转变化。

更标准的做法是基于**冲量**。

### 接触点相对速度

设接触点相对刚体质心的位置向量为 `rA`、`rB`，则接触点速度为：

```text
v_contact = v_linear + ω × r
```

两个刚体在接触点的相对速度：

```text
v_rel = (vB + ωB × rB) - (vA + ωA × rA)
```

如果：

```text
dot(v_rel, n) > 0
```

说明它们沿法线方向已经在分离，就不应该继续施加法向冲量。

### 法向冲量公式

最常见的法向冲量标量 `j` 可写成：

```text
j =
-(1 + e) * dot(v_rel, n)
---------------------------------------------
invMassA + invMassB
+ (cross(rA, n)^2) * invIA
+ (cross(rB, n)^2) * invIB
```

其中：

- `e` 是恢复系数（弹性）
- `n` 是接触法线
- `invIA`、`invIB` 是逆惯量

得到冲量后：

```text
impulse = j * n

vA -= impulse * invMassA
ωA -= invIA * cross(rA, impulse)

vB += impulse * invMassB
ωB += invIB * cross(rB, impulse)
```

这就是“碰撞不只改位置，也改速度与角速度”的关键。

### 摩擦为什么要单独算

法向冲量只负责“别继续相互穿进去”，不会处理切向滑动。  
因此摩擦通常沿接触切线 `t` 再求一个切向冲量 `jt`：

```text
t = normalize(v_rel - dot(v_rel, n) * n)
```

再把 `jt` 限制在库仑摩擦圆锥的近似范围里：

```text
|jt| <= μ * j
```

这一步做完，物体落地后才会呈现“滑、停、滚”的差异。

🌌🌌🌌

## 🔗 约束求解：接触、关节、摩擦，本质上都能写成约束

如果把物理引擎再往前推进一步，你会发现很多问题都能统一成“约束”：

- 接触约束：不允许两个物体继续互相穿透
- 距离关节：两个锚点距离保持恒定
- 转动关节：只允许绕某点旋转
- 摩擦约束：限制切向相对运动

### 约束的统一形式

连续世界中的约束可以写成：

```text
C(q) = 0
```

其中 `q` 是位置与姿态组成的广义坐标。

进一步到速度层，可写成：

```text
Jv + b = 0
```

这里：

- `J` 是约束雅可比矩阵
- `v` 是广义速度
- `b` 是偏置项，常用于误差修正和恢复

求解器要找的不是“位置答案”，而是一个约束冲量 `λ`，使系统速度在迭代后更满足约束。

### 为什么实际引擎爱用迭代法

因为真实场景接触很多、约束很多、互相耦合很强。  
直接构造并求解一个庞大的全局线性系统，代价高、实现复杂，也不一定适合实时游戏。

因此许多实时物理引擎会采用：

- Sequential Impulses
- Projected Gauss-Seidel
- warm starting
- velocity iterations + position iterations

可以把它理解成：

> 不一次性求出全局完美解，而是反复扫过所有接触和关节，让系统逐渐收敛到“足够稳定”的状态。

### 顺序冲量法伪代码

```text
for iter in 1..N:
    for contact in contacts:
        compute relative velocity
        compute normal impulse increment
        clamp accumulated normal impulse >= 0
        apply impulse to both bodies

        compute tangent impulse increment
        clamp friction impulse to [-μPn, μPn]
        apply friction impulse
```

这里的关键思想有两个：

1. **累积冲量**：不是每轮从零算，而是在旧值基础上增量更新
2. **投影 / clamp**：接触约束是单边约束，法向冲量不能变成“拉住物体”的负值

这也是 Box2D 一类实时引擎中非常核心的工程思想。

### 位置修正与 Baumgarte 稳定化

即便速度约束求得不错，离散积分仍可能造成少量穿透。  
常见修正方式之一是把穿透量转成偏置项：

```text
bias = -β / dt * max(0, penetration - slop)
```

其中：

- `β` 是修正强度
- `slop` 是允许的小误差

这样求解器会在后续迭代中主动把穿透往外推一点。  
如果没有误差修正，堆叠物体通常会逐帧下沉。

🌌🌌🌌

## 🧠 一个最小可用的物理引擎应包含哪些模块

| 模块 | 作用 | 先做什么 |
| --- | --- | --- |
| `Body` | 保存刚体状态 | 圆形、盒体、静态地面 |
| `Shape` | 几何描述 | Circle + Convex Box |
| `BroadPhase` | 快速配对 | 先用朴素 AABB，两两筛选 |
| `NarrowPhase` | 生成接触信息 | Circle-Circle、Box-Box(SAT) |
| `ContactManifold` | 保存接触点、法线、穿透深度 | 先支持 1 个接触点也行 |
| `Solver` | 求法向/摩擦/关节冲量 | 先做顺序冲量 |
| `World` | 管理步进流程 | 固定 `dt`、迭代次数 |

很多教程一开始就想做：

- 多种复杂形状
- 连续碰撞检测 CCD
- 各种关节系统
- 多线程广相位
- 完整 3D

这很容易把项目拖入“全都懂一点，但没有闭环”的状态。  
更现实的路线是：

1. 先做圆 + 静态平面
2. 再做 AABB / 盒体
3. 再做 SAT 接触
4. 再做摩擦
5. 再做关节
6. 最后才考虑 CCD、睡眠、岛屿、BVH

🌌🌌🌌

## 🧪 极简伪代码：从一步世界更新看全局结构

```cpp
void PhysicsStep(World& world, float dt) {
    const int velocityIterations = 8;
    const int positionIterations = 3;

    // 1. 积分外力，得到预测速度
    for (Body& b : world.bodies) {
        if (b.invMass == 0.0f) continue;
        b.velocity += (world.gravity + b.force * b.invMass) * dt;
        b.angularVelocity += b.torque * b.invInertia * dt;
    }

    // 2. 宽相位 + 窄相位，生成接触流形
    world.contacts = BuildContacts(world);

    // 3. 预计算有效质量、偏置、切线，并可做 warm start
    PreStep(world.contacts, dt);

    // 4. 速度层迭代求解
    for (int i = 0; i < velocityIterations; ++i) {
        for (Contact& c : world.contacts) {
            SolveNormalImpulse(c);
            SolveTangentImpulse(c);
        }
    }

    // 5. 用修正后的速度推进位置
    for (Body& b : world.bodies) {
        if (b.invMass == 0.0f) continue;
        b.position += b.velocity * dt;
        b.angle += b.angularVelocity * dt;
    }

    // 6. 可选：位置层迭代修正残余穿透
    for (int i = 0; i < positionIterations; ++i) {
        SolvePositionConstraints(world.contacts);
    }

    // 7. 清力
    for (Body& b : world.bodies) {
        b.force = Vec2(0, 0);
        b.torque = 0.0f;
    }
}
```

如果你能把这条主循环真正跑通，并稳定地表现出“落地、堆叠、弹跳、摩擦滑动”，那就已经不是玩具演示，而是一个具有物理引擎核心骨架的系统了。

🌌🌌🌌

## 📐 理解公式时最容易忽略的几个点

### 1. 旋转项不能省

只做线速度响应，很多碰撞看起来“能跑”，但箱子被撞边缘时不会合理自转。  
接触点不在质心上时，角速度变化来自：

```text
τ = r × F
```

冲量形式下对应：

```text
Δω = invI * (r × J)
```

这决定了为什么“撞中心”和“撞边角”的效果完全不同。

### 2. 接触点速度不是质心速度

很多错误都来自直接拿 `vA - vB` 当相对速度。  
真正接触发生在接触点，必须包含角速度贡献：

```text
v_point = v + ω × r
```

### 3. 穿透修正和速度求解是两回事

“把位置推开”解决的是几何重叠。  
“施加冲量”解决的是速度层的动量与约束。  
这两件事混在一起写，代码会很快变得不可控。

### 4. 物理引擎最怕单位混乱

建议一开始就固定一套单位，例如：

- 长度：米
- 质量：千克
- 时间：秒

如果贴图像素和物理世界长度混用，调参会非常痛苦。

🌌🌌🌌

## 🚨 常见坑

| 坑 | 现象 | 原因 |
| --- | --- | --- |
| 直接用可变 `dt` | 不同机器表现不同 | 数值稳定性被时间步长破坏 |
| 只做位置推开 | 物体像黏土一样分开 | 没有处理冲量与角速度 |
| 没有摩擦 | 落地后一直滑 | 只解了法向约束 |
| 没有 bias/slop | 堆叠下沉或抖动 | 穿透误差无法收敛 |
| 没有 warm starting | 接触响应发软 | 每帧从零迭代，收敛慢 |
| 先做太多形状 | 调试爆炸 | 问题源头难定位 |

一个很实用的调试顺序是：

1. 先画 AABB
2. 再画接触法线
3. 再画接触点速度
4. 最后再调摩擦与恢复系数

只有可视化足够强，你才知道错误是在**检测阶段**还是**求解阶段**。

🌌🌌🌌

## 🛠️ 建议学习路径

### Phase 1：先做最小闭环

- 重力
- 圆形刚体
- 静态地面
- 半隐式欧拉
- 圆与圆 / 圆与平面碰撞
- 法向冲量

目标：看见物体能稳定下落、弹起、停止穿透。

### Phase 2：让系统开始“像引擎”

- 盒体或凸多边形
- AABB 宽相位
- SAT
- 摩擦
- 多接触点
- 堆叠稳定性

目标：箱子能堆起来，碰撞不明显发散。

### Phase 3：进入工程化

- 关节
- 睡眠机制
- 持续接触缓存
- warm starting
- CCD / TOI
- Dynamic BVH

目标：系统性能、稳定性、复杂场景表现都明显提升。

🌌🌌🌌

## 📚 学习资源推荐

下面这组资料的学习顺序，我建议按“入门直觉 -> 代码骨架 -> 求解器思想 -> 更系统的碰撞检测”来走。

| 资源 | 类型 | 推荐理由 |
| --- | --- | --- |
| [Box2D 官方文档](https://box2d.org/documentation/) | 文档 | 了解现代 2D 物理引擎的整体模块划分 |
| [Box2D-Lite](https://github.com/erincatto/box2d-lite) | 源码 | 体量小，适合直接读“最小可讲清楚的引擎骨架” |
| [Fast and Simple Physics using Sequential Impulses](https://box2d.org/files/ErinCatto_SequentialImpulses_GDC2006.pdf) | 幻灯 / 论文式讲义 | 冲量求解与约束迭代的经典材料 |
| [How Do Physics Engines Work](https://github.com/erincatto/box2d-lite/tree/master/docs) | 讲义 | 站在实现者视角看一个物理引擎的组成 |
| [Gaffer On Games: Integration Basics](https://gafferongames.com/post/integration_basics/) | 文章 | 用极清楚的方式讲积分器与误差 |
| [Gaffer On Games: Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/) | 文章 | 理解为什么固定步长几乎是实时物理的默认答案 |
| [Real-Time Collision Detection](https://books.google.com/books/about/Real_Time_Collision_Detection.html?id=4wTNBQAAQBAJ) | 书籍 | 碰撞检测领域的经典参考书 |
| [Box2D 官方仓库](https://github.com/erincatto/box2d) | 生产级源码 | 在掌握 Lite 版本后，对照真实工程实现差异 |
| [Dynamic Bounding Volume Hierarchies](https://box2d.org/files/ErinCatto_DynamicBVH_Full.pdf) | 讲义 | 宽相位加速结构的进阶材料 |

### 一个比较稳的阅读顺序

1. 先看 `Integration Basics` 和 `Fix Your Timestep!`，建立时间推进直觉
2. 再读 `Box2D-Lite`，理解世界步进、接触、冲量求解主循环
3. 接着看 `Sequential Impulses`，把“为什么这样解约束”真正想通
4. 最后读 `Real-Time Collision Detection`，把碰撞检测从“会用”推进到“会设计”

🌌🌌🌌

## 🌒 总结

从零开始构建物理引擎，最容易误判的地方是：以为它的难点在数学公式多。  
其实更难的是把这些公式放进一个**离散、迭代、近似、实时**的系统后，仍然让它稳定工作。

真正需要建立的理解是：

- 刚体动力学负责“自由运动”
- 碰撞检测负责“找到几何约束”
- 冲量与约束求解负责“把几何约束转成速度修正”
- 固定时间步长、误差修正、warm starting 负责“把系统拉回稳定区间”

如果只用一句话概括这门主题，我会写成：

> 物理引擎不是在模拟“真实世界”，而是在每一帧里，持续求一个**足够稳定、足够快、足够像真的近似解**。

