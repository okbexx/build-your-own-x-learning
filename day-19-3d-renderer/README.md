---
day: 19
topic: 3D Renderer
status: done
source_repo: https://github.com/codecrafters-io/build-your-own-x
---

# Day 19 · 3D Renderer

> 一句话概括：3D 渲染器的核心不是“画出精美图形”，而是把一套“几何表示→坐标变换→光栅化→着色”的管线稳定输出为像素。

## build-your-own-x 对应原始项目地址

- https://github.com/codecrafters-io/build-your-own-x#build-your-own-3d-renderer
- 推荐学习：tinyrenderer https://github.com/ssloy/tinyrenderer

## 这是什么

如果把图形界面里的“画一个三角形”“贴一张纹理”理解成调用现成 API，那么你看到的只是最外层的按钮，而不是机器内部真正运转的机构。3D 渲染器的意义，恰恰在于把这套机构从零拆开，再一层层重新装回去。

一个 3D 渲染器，本质上是在回答一个冷静而精确的问题：给定场景中的物体、相机、光源和材质，最终屏幕上每一个像素应该是什么颜色。这个问题听起来像“绘图”，实际上更接近“数值计算 + 几何变换 + 可见性判断 + 局部光照近似”的综合系统工程。你不是在命令系统“帮我画个盒子”，而是在亲手实现一条视觉输出管线，让空间中的三角形，经过坐标系变换、投影压缩、离散采样、深度竞争和着色计算，最终落成屏幕上一块块有限分辨率的像素。

从几何角度看，渲染器处理的是点、向量、法线、矩阵、三角网格。3D 模型最常见的形式不是“物体”这个抽象词，而是大量顶点和面片的组合。每个顶点先存在于模型自己的局部坐标系里，随后被放到世界中，再转换到相机视角下，最后投影到二维平面。这个过程中，所谓“看到一个立方体”，其实是看到一串数学变换把三维位置映射成屏幕坐标的结果。

从光学角度看，渲染器并不真的模拟完整物理世界，但它会借助简化模型近似“亮”和“暗”为何出现。漫反射解释了为什么正对光的表面更亮，镜面反射解释了为什么某些边缘会冒出锐利高光，法线则决定了表面朝向如何影响入射能量。即便是最基础的 Phong 或 Blinn-Phong，也已经足够让一张平面的三角网格获得立体感。

从计算角度看，渲染器是一台严格的流水线机器。它不关心“这张图像有没有艺术感”，它关心的是：投影矩阵是否正确、边缘函数是否稳定、深度比较是否一致、插值是否发生透视失真、像素覆盖规则是否漏缝。很多新手第一次写渲染器时，会误以为它是“会调用画线和填充函数的程序”；真正写下去才会发现，它更像一个微型图形处理器的软件模拟版。你得自己决定哪个像素被哪个三角形覆盖，谁挡住谁，哪个点该采样哪块纹理，以及高光为什么会落在那个位置。

所以，学习 3D 渲染器的价值，不只是“能画出一个头模”或“能跑出一个旋转立方体”。更重要的是，你会重新理解现代图形系统的底层秩序：为什么 GPU 以三角形为基本单位，为什么矩阵乘法是图形学的日常语言，为什么 Z-buffer 这种看似朴素的数组能决定一整个场景的遮挡关系。黑色屏幕上亮起的每个像素，背后都不是魔法，而是一条被你亲手实现、逐步校准的计算链路。

## 核心概念与原理

### 1. 坐标变换与投影

3D 渲染的第一件事，不是画，而是“搬运坐标”。一个顶点会经历模型坐标系、世界坐标系、观察坐标系、裁剪空间，再映射到屏幕空间。你可以把它理解为：先决定物体放在哪，再决定相机从哪看，最后决定如何把透视效果压扁到二维屏幕。

```python
import math

def mat4_mul_vec4(m, v):
    # 4x4 矩阵乘以齐次坐标向量
    return [
        sum(m[0][i] * v[i] for i in range(4)),
        sum(m[1][i] * v[i] for i in range(4)),
        sum(m[2][i] * v[i] for i in range(4)),
        sum(m[3][i] * v[i] for i in range(4)),
    ]

def project_vertex(vertex, model, view, proj, width, height):
    x, y, z = vertex
    v = [x, y, z, 1.0]

    # 模型 -> 世界 -> 观察 -> 裁剪
    world = mat4_mul_vec4(model, v)
    camera = mat4_mul_vec4(view, world)
    clip = mat4_mul_vec4(proj, camera)

    # 透视除法，进入 NDC
    ndc_x = clip[0] / clip[3]
    ndc_y = clip[1] / clip[3]
    ndc_z = clip[2] / clip[3]

    # NDC [-1, 1] 映射到屏幕像素
    screen_x = int((ndc_x + 1.0) * 0.5 * width)
    screen_y = int((1.0 - ndc_y) * 0.5 * height)
    return screen_x, screen_y, ndc_z
```

这一节最容易踩的坑有两个：一是矩阵乘法顺序写反，二是忘记透视除法。前者会让模型像被错误坐标系撕扯，后者会让“远小近大”完全失效。

### 2. 光栅化

投影之后，你拿到的是屏幕上的三角形轮廓，但屏幕真正能显示的是像素格子。光栅化的任务，就是判断哪些像素被三角形覆盖，并计算这些像素内部对应的插值信息。常见方法包括边界框检测、边缘函数、扫描线算法，以及基于重心坐标的覆盖判断。

```python
def edge(a, b, p):
    # 边缘函数：判断点 p 在边 ab 的哪一侧
    return (p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])

def raster_triangle(v0, v1, v2):
    min_x = int(min(v0[0], v1[0], v2[0]))
    max_x = int(max(v0[0], v1[0], v2[0]))
    min_y = int(min(v0[1], v1[1], v2[1]))
    max_y = int(max(v0[1], v1[1], v2[1]))

    area = edge(v0, v1, v2)
    pixels = []

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            p = (x + 0.5, y + 0.5)  # 采样像素中心
            w0 = edge(v1, v2, p)
            w1 = edge(v2, v0, p)
            w2 = edge(v0, v1, p)

            # 三个符号一致，说明点在三角形内
            if w0 >= 0 and w1 >= 0 and w2 >= 0:
                alpha = w0 / area
                beta = w1 / area
                gamma = w2 / area
                pixels.append((x, y, alpha, beta, gamma))

    return pixels
```

这里的关键不只是“填满三角形”，而是要稳定地决定覆盖关系。真正进入工程实现后，你会开始处理 top-left rule、共边像素、子像素精度、裂缝和抖动问题。也就是说，光栅化不是粗暴涂色，而是离散几何在像素网格上的严格投影。

### 3. 深度缓冲与隐藏表面消除

如果场景里只有一个三角形，你只需要画出来；一旦出现多个面片重叠，就必须决定前后遮挡关系。Z-buffer 的思想非常直接：每个像素额外保存一个深度值，新的片元只有在更靠近相机时，才能覆盖旧颜色。

```c
void draw_fragment(
    int x, int y,
    float z,
    unsigned int color,
    float *zbuffer,
    unsigned int *framebuffer,
    int width
) {
    int idx = y * width + x;

    // 深度越小，说明越靠近相机
    if (z < zbuffer[idx]) {
        zbuffer[idx] = z;
        framebuffer[idx] = color;
    }
}
```

Z-buffer 看起来只是两个数组比较大小，但它是实时图形里最重要的秩序维护者之一。没有它，后画的物体会机械地盖住先画的物体，整个三维世界立刻退化成平面的涂层堆叠。进一步你还会碰到深度精度、近平面设置、z-fighting、反向 Z 等问题，它们都说明“谁在前面”这件事远比表面看上去复杂。

### 4. 着色模型与光照

确定像素属于哪个三角形之后，还要回答“它该多亮”。最基础的做法，是用法线和光源方向计算漫反射，再叠加镜面反射形成高光。Phong 和 Blinn-Phong 虽然不是物理真实渲染，但它们结构清晰、易于实现，非常适合作为自制渲染器的起点。

```python
def normalize(v):
    length = sum(i * i for i in v) ** 0.5
    return [i / length for i in v]

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def blinn_phong(normal, light_dir, view_dir, base_color):
    n = normalize(normal)
    l = normalize(light_dir)
    v = normalize(view_dir)
    h = normalize([l[0] + v[0], l[1] + v[1], l[2] + v[2]])  # 半角向量

    ambient = 0.1
    diffuse = max(dot(n, l), 0.0)
    specular = max(dot(n, h), 0.0) ** 32

    intensity = ambient + 0.7 * diffuse + 0.2 * specular
    return [min(int(c * intensity), 255) for c in base_color]
```

这段计算的本质，是把“表面朝向”和“观察方向”映射成亮度变化。它并不追求绝对真实，但足够让你观察到体积感、棱角和高光。很多人第一次写出会发亮的模型时，才真正理解法线不是附属数据，而是决定表面视觉性格的核心变量。

### 5. 纹理映射与插值

当纯色三角形已经不够表达细节时，你会把二维图像贴到三维表面上，这就是纹理映射。每个顶点除了位置，还带有 UV 坐标；渲染时通过插值求出像素对应的 UV，再去纹理图中采样颜色。若要避免块状感，可以使用双线性插值；若要避免透视变形，则要做透视校正插值，而不是直接线性混合屏幕空间 UV。

```python
def bilinear_sample(texture, u, v):
    h = len(texture)
    w = len(texture[0])

    x = u * (w - 1)
    y = v * (h - 1)
    x0, y0 = int(x), int(y)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)

    tx = x - x0
    ty = y - y0

    c00 = texture[y0][x0]
    c10 = texture[y0][x1]
    c01 = texture[y1][x0]
    c11 = texture[y1][x1]

    # 双线性插值：先横向，再纵向
    def lerp(a, b, t):
        return [a[i] * (1 - t) + b[i] * t for i in range(3)]

    top = lerp(c00, c10, tx)
    bottom = lerp(c01, c11, tx)
    return lerp(top, bottom, ty)

def perspective_correct_uv(alpha, beta, gamma, uv0, uv1, uv2, w0, w1, w2):
    # 使用重心坐标做透视校正，避免纹理拉伸
    inv_w = alpha / w0 + beta / w1 + gamma / w2
    u = (alpha * uv0[0] / w0 + beta * uv1[0] / w1 + gamma * uv2[0] / w2) / inv_w
    v = (alpha * uv0[1] / w0 + beta * uv1[1] / w1 + gamma * uv2[1] / w2) / inv_w
    return u, v
```

很多教程会先教“直接插值 UV”，因为它实现最短；但一旦三角形有明显透视缩放，你会看到纹理像橡胶一样被扭曲。那一刻你会明白，纹理映射不是简单贴图，而是三维投影下的参数重建问题。

## 最小实现路径

从零开始做一个简单 3D 渲染器，建议按下面的路径推进，不要一上来就追求完整光照、阴影或抗锯齿。先把最小闭环跑通，再逐层叠能力。

1. 读取 `.obj` 或自定义三角网格。先能拿到顶点位置、面索引，最好再支持法线和 UV。
2. 实现矩阵/向量类。至少具备加减乘、点积、叉积、归一化、4x4 矩阵乘法。
3. 实现 `model/view/projection` 变换。先让一个立方体能被正确投影到屏幕。
4. 绘制线框和填充三角形。线框帮助调试拓扑，填充帮助验证光栅化逻辑。
5. 加入深度测试。此时模型应当具备正确遮挡关系，不再“后画覆盖前画”。
6. 加入基础着色。先做法线可视化，再做 Lambert 或 Blinn-Phong，会更容易定位错误。
7. 加入纹理映射。最后处理 UV、透视校正和双线性采样，让表面获得细节。

如果你想控制复杂度，一个很稳的策略是：每完成一步，都导出一张静态图像检查结果，而不是同时调试旋转动画、输入系统和文件加载器。渲染器最怕的不是代码多，而是错误被多条链路同时掩盖。

## 推荐资源

- `tinyrenderer`：极其经典，代码量不大，但能把软件渲染器的核心路径讲得非常透。
- `Scratchapixel`：图形学入门质量很高，尤其适合理解投影、坐标系、光线与插值。
- 《Computer Graphics: Principles and Practice》：体系完整，适合长期做案头参考。
- 《Fundamentals of Computer Graphics》：比大部头更适合工程型学习者切入。
- LearnOpenGL：虽然主线是现代 OpenGL，但对坐标变换、光照、纹理等基础章节解释清楚。
- tinyobjloader、Assimp：当你不想自己写复杂模型解析器时，可以参考它们的数据组织方式。
- Mesa 以及各类软件光栅器实现：适合在掌握基础后观察“工业实现如何处理边角问题”。

## 今日思考题

1. 如果把渲染器从“面向三角形”改成“面向体素”或“面向隐式曲面”，整条管线里哪些步骤还能复用，哪些步骤必须重写？
2. Z-buffer 非常高效，但它并不直接告诉你“为什么这个像素被挡住”。如果要支持透明物体、次表面散射或多层材质，现有深度模型会在哪些地方失效？
3. 在实时渲染里，我们大量使用近似：近似光照、近似可见性、近似采样。如果算力无限，你会优先替换哪一个近似环节，为什么？
