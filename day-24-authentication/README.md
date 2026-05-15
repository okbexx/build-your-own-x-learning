---
day: 24
topic: Authentication / Login
status: done
date: 2026-05-15
source_repo: https://github.com/codecrafters-io/build-your-own-x
---

# Day 24 · Authentication / Login

> `IDENTITY PROOF // SESSION BINDING // TRUST BOUNDARY`
>
> 登录系统不是“做一个表单，再查一下数据库”。
> 它本质上是在解决三个连续问题：
> 你是谁、系统如何持续确认还是你、系统凭什么在后续请求中继续信任你。

---

## 先分清：认证、授权、会话

- 认证 `Authentication`：证明“你是谁”
- 授权 `Authorization`：决定“你能做什么”
- 会话管理 `Session Management`：决定“你如何跨多个请求维持登录状态”

很多工程问题都来自这三者混在一起。

- Cookie 不是认证
- Session 不是授权
- JWT 不是安全本身
- OAuth2 也不等于“登录协议”

HTTP 是无状态的。浏览器每发一次请求，服务端理论上都应该重新回答一句：

> 这是谁发来的请求？我为什么相信它？

认证系统，就是围绕这句追问建立的一整套机制。

---

## 为什么要自己实现

“自己实现”这里更准确的意思不是“生产环境手搓密码学”，而是：

> 亲手把认证链路搭一遍，理解它的状态边界、攻击面和设计折中。

原因很现实：

- 框架能帮你接线，但不会替你理解信任模型
- 真正的线上事故，往往不是库不会用，而是边界判断错了
- 认证是很多系统的总入口，一旦设计失误，后面所有权限控制都会失去基础
- 只有自己实现过，才知道哪些细节绝不能省

具体能学到什么：

- 为什么密码必须使用慢哈希，而不是 `SHA-256(password)`
- 为什么 Session ID 必须是高熵随机值，不能可预测
- 为什么 JWT 更像“可验证声明”，而不是“万能登录状态”
- 为什么 OAuth2 解决的是委托授权，OpenID Connect 才真正补上身份层
- 为什么 MFA 提高的是攻击成本，不是绝对安全

学习上建议自己实现，生产上建议优先使用成熟库和成熟协议，不要自创加密算法、签名格式或 Token 规范。

---

## 认证系统到底在解决什么

可以把一次完整登录抽象成下面这条链路：

```text
[用户提交身份凭据]
        |
        v
[服务端验证凭据是否成立]
        |
        v
[创建可持续验证的登录状态]
        |
        v
[客户端在后续请求中携带状态]
        |
        v
[服务端恢复用户身份]
        |
        v
[授权系统决定能访问什么]
```

这里最核心的不是“登录页”，而是两次证明：

1. 初次证明：用户名密码、短信码、TOTP、WebAuthn、第三方身份提供方
2. 持续证明：Session Cookie、Access Token、Refresh Token、SSO 断言

所以认证系统的本质，不是一次性校验，而是把“身份证明”安全地延续到后续请求。

---

## 核心原理

### 1. 密码不是存起来，而是只存“验证能力”

服务端绝不应该保存明文密码。理想状态是：

- 你知道用户密码是否正确
- 但你永远不知道密码原文

这就需要密码哈希。

#### 为什么不能直接用普通哈希

像 `MD5`、`SHA-1`、`SHA-256` 这类通用哈希函数设计目标是“快”，而密码存储恰恰需要“慢”。

攻击者一旦拿到数据库，如果哈希计算太快，就能高速跑字典、撞库和彩虹表。

密码存储应该用：

- `Argon2id`：当前通用推荐
- `scrypt`
- `bcrypt`

它们的共同点是：**故意让猜密码变贵**。

#### 什么是 salted hash

盐 `salt` 是每个用户独立生成的一段随机值，和密码一起参与哈希：

```text
stored_hash = KDF(password + salt)
```

盐的作用：

- 避免相同密码生成相同结果
- 阻止预计算彩虹表直接复用
- 让攻击者必须逐条记录分别爆破

盐不需要保密，通常和哈希一起存储。真正的价值在于“每个账户都不同”。

#### pepper 是什么

`pepper` 是额外的全局秘密，通常存环境变量或 HSM，不和数据库放在一起：

```text
stored_hash = KDF(password + salt + pepper)
```

它不是替代盐，而是增加数据库泄漏后的额外阻力。

#### 最小密码哈希示意

```python
# Python 伪代码
from secrets import token_bytes

def hash_password(password: str) -> str:
    salt = token_bytes(16)
    # Argon2id 参数示意：memory/time/parallelism 需按环境调优
    return argon2id_hash(password=password + PEPPER, salt=salt)

def verify_password(password: str, stored_hash: str) -> bool:
    return argon2id_verify(password=password + PEPPER, encoded_hash=stored_hash)
```

关键点：

- 不要自己设计哈希格式
- 不要自己拼接字节细节
- 直接使用成熟库输出的标准编码结果

---

### 2. Session 与 Cookie：最经典也最稳的登录状态模型

HTTP 无状态，所以服务端必须想办法把“这次已登录”延续到下次请求。

最常见的做法是：

- 服务端创建一条 Session 记录
- 生成一个高熵 Session ID
- 浏览器用 Cookie 持有这个 Session ID
- 之后每次请求自动带上 Cookie
- 服务端用 Session ID 查回用户身份

#### 一句话理解

- `Session`：服务端保存的登录状态
- `Cookie`：浏览器保存并自动携带的小数据容器

Cookie 只是“载体”，不是认证本身。真正的登录状态通常在服务端。

#### 典型 Session 流程

```text
用户提交账号密码
  -> 服务端验证成功
  -> 创建 session(user_id, expires_at, ...)
  -> 生成随机 sid
  -> Set-Cookie: sid=...
  -> 浏览器后续请求自动带上 sid
  -> 服务端查 session 恢复身份
```

#### Cookie 的关键安全属性

- `HttpOnly`：前端 JS 不能直接读取，降低 XSS 窃取 Cookie 的风险
- `Secure`：只允许通过 HTTPS 发送
- `SameSite=Lax/Strict`：降低跨站请求伪造 `CSRF`
- `Max-Age/Expires`：控制有效期
- `Path/Domain`：限制作用范围

如果这是你的第一个认证系统，默认建议是：

```text
HttpOnly + Secure + SameSite=Lax
```

#### Session ID 的要求

Session ID 绝不能：

- 可预测
- 可枚举
- 包含用户 ID、时间戳等可推断信息

它应该只是足够长的随机字符串，例如 256 bit 随机值。

#### Session 的典型问题

- Session 固定攻击 `Session Fixation`
  登录成功后要旋转 Session ID，避免攻击者提前种入旧 ID
- CSRF
  因为浏览器会自动带 Cookie，所以跨站表单也可能携带登录态
- 服务端状态管理
  需要数据库或 Redis 来保存和过期清理 Session

---

### 3. JWT：可验证声明，不是银弹

JWT `JSON Web Token` 看起来像一个字符串，实际上是：

```text
base64url(header).base64url(payload).base64url(signature)
```

它的核心价值是：

- 服务端不用查库也能验证签名
- 多服务之间可以共享验证逻辑
- 很适合 API、网关、跨服务传递身份声明

但要特别注意：

> JWT 默认是签名，不是加密。Payload 通常可读，不要把敏感信息直接放进去。

#### JWT 里常见字段

- `sub`：主体，一般是用户 ID
- `iss`：签发者
- `aud`：受众
- `exp`：过期时间
- `iat`：签发时间
- `jti`：唯一 ID，可辅助撤销和审计

#### 最小 JWT 示例

```javascript
// Node.js 伪代码
const token = jwt.sign(
  {
    sub: user.id,
    role: user.role,
    aud: "api",
    iss: "auth.example.com"
  },
  PRIVATE_KEY,
  {
    algorithm: "RS256",
    expiresIn: "15m",
    jwtid: randomUUID()
  }
)
```

验证时看三件事：

- 签名是否有效
- `iss / aud / exp` 是否符合预期
- 当前业务是否还接受这枚 Token

#### JWT 的优点

- 无状态验证，横向扩展简单
- 适合多服务、API Gateway、移动端
- 可把身份声明快速带到下游服务

#### JWT 的代价

- 颁发后难以立即撤销
- 容易被误用为“长期登录状态”
- 一旦放进 `localStorage` 并遭遇 XSS，风险很高

实践里常见组合是：

- 短期 `access token`
- 长期 `refresh token`
- 刷新时重新签发

如果你的场景只是普通 Web 应用登录，Session Cookie 通常比 JWT 更简单、更稳。

---

### 4. OAuth2：它解决的是“委托授权”

OAuth2 的问题意识不是“用户怎么登录到你的网站”，而是：

> 用户如何授权第三方应用，代表自己去访问另一个服务的资源。

典型场景：

- 某个应用请求访问你的 GitHub 仓库
- 某个 SaaS 请求读取你的 Google 日历

这里的核心角色有四个：

- `Resource Owner`：资源所有者，通常是用户
- `Client`：第三方应用
- `Authorization Server`：授权服务器
- `Resource Server`：真正持有资源的 API

#### 为什么很多人把 OAuth2 和登录混在一起

因为现实世界中，很多“使用 Google 登录”其实是：

- 用 OAuth2 拿到授权流程
- 再用 OpenID Connect `OIDC` 在其上补充身份信息

所以更准确的说法是：

- `OAuth2`：授权框架
- `OIDC`：身份层，解决“这个用户是谁”

#### 现代推荐流程：Authorization Code + PKCE

```text
浏览器跳转到身份提供方
  -> 用户完成登录与同意授权
  -> 身份提供方返回 authorization code
  -> 客户端用 code + code_verifier 换 token
  -> 获得 access token / id token
```

为什么要 `PKCE`：

- 防止 code 被截获后直接兑换 Token

为什么要 `state`：

- 防止登录回调链路被 CSRF 劫持

为什么 OIDC 里还要 `nonce`：

- 防止 ID Token 被重放到不相干的认证请求

---

### 5. SSO：一次登录，多系统信任

单点登录 `SSO` 的目标是：

> 用户在统一身份提供方登录一次，多个业务系统共享这份身份结果。

常见实现方式：

- 企业内部：OIDC、SAML
- 互联网产品矩阵：统一账号中心 + OIDC

SSO 的收益：

- 用户体验统一
- 账号体系集中
- 权限与审计更容易收口

SSO 的代价：

- 身份提供方变成关键单点
- 一旦主认证中心出问题，影响面会很大
- Token、断言、登出联动会更复杂

如果你要“自己实现”，建议先做单应用 Session，再做 OIDC Provider/Consumer，最后再考虑 SSO。

---

### 6. MFA：在密码之外增加第二条证明链

多因素认证 `MFA` 的核心思想是：

> 只知道密码还不够，还要再提供另一类证明。

常见因素：

- 你知道什么：密码、PIN
- 你持有什么：手机、硬件密钥
- 你是什么：生物特征

常见方案从强到弱大致可以理解为：

- `WebAuthn / Passkey`
- `TOTP`
- `短信验证码`

为什么短信通常不作为首选：

- 容易遭遇 SIM Swap
- 依赖运营商链路
- 抗钓鱼能力较弱

MFA 不是绝对安全，它只是显著提高攻击成本。  
在高风险操作里，还可以做 `step-up authentication`，例如修改邮箱、关闭 MFA、导出敏感数据时再次验证。

---

## 最小可行实现（MVP）

如果目标是“自己实现一个真正可跑、又不至于过度复杂的登录系统”，最推荐的 MVP 不是 JWT，也不是 OAuth2，而是：

> 用户名/邮箱 + 密码 + 服务端 Session + 安全 Cookie

这是最适合理解认证主干的起点。

### MVP 功能范围

第一版只做这些：

- 用户注册
- 用户登录
- 用户登出
- 登录态恢复
- 受保护路由
- 密码哈希存储
- 基础失败限流

先不要急着做：

- 社交登录
- SSO
- JWT 网关分发
- 复杂设备管理
- 自己实现短信服务

### MVP 数据模型

```text
users
- id
- email
- password_hash
- created_at
- updated_at

sessions
- id
- user_id
- expires_at
- revoked_at
- created_at
- last_seen_at
- ip_hash
- user_agent_hash
```

一个很实用的细节是：

> 数据库里不要直接存原始 `sid`，而是存它的哈希。

这样即使 Session 表泄漏，攻击者也不能直接拿表里的值冒充登录态。

### MVP 登录流程

```text
POST /login
  -> 查用户
  -> 验证密码哈希
  -> 失败则记录审计与限流
  -> 成功则创建 session
  -> Set-Cookie: sid=...
  -> 后续请求中间件根据 sid 识别用户
```

### Session 方案伪代码

```python
# Python 伪代码
import secrets

def register(email: str, password: str):
    email = normalize_email(email)
    ensure_password_policy(password)
    password_hash = hash_password(password)
    db.users.insert({
        "email": email,
        "password_hash": password_hash,
    })

def login(email: str, password: str, request):
    email = normalize_email(email)
    user = db.users.find_one({"email": email})

    ok = bool(user) and verify_password(password, user["password_hash"])
    if not ok:
        rate_limit_hit(key=f"login:{request.ip}")
        audit("login_failed", email=email, ip=request.ip)
        raise AuthError("invalid credentials")

    raw_sid = secrets.token_urlsafe(32)
    db.sessions.insert({
        "id": sha256(raw_sid),
        "user_id": user["id"],
        "expires_at": now() + days(7),
        "created_at": now(),
        "ip_hash": sha256(request.ip),
        "user_agent_hash": sha256(request.user_agent),
    })

    response = redirect("/dashboard")
    response.set_cookie(
        "sid",
        raw_sid,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=7 * 24 * 3600,
        path="/",
    )
    audit("login_success", user_id=user["id"])
    return response

def current_user(request):
    raw_sid = request.cookies.get("sid")
    if not raw_sid:
        return None

    session = db.sessions.find_one({"id": sha256(raw_sid)})
    if not session:
        return None
    if session["revoked_at"] is not None:
        return None
    if session["expires_at"] < now():
        return None

    return db.users.find_by_id(session["user_id"])

def logout(request, response):
    raw_sid = request.cookies.get("sid")
    if raw_sid:
        db.sessions.update(
            {"id": sha256(raw_sid)},
            {"revoked_at": now()}
        )
    response.delete_cookie("sid", path="/")
```

### 这个 MVP 为什么值得先做

因为它逼你直接面对最核心的认证问题：

- 凭据如何验证
- 登录状态如何创建
- 状态如何跨请求延续
- 状态如何撤销
- 失败尝试如何审计和限流

一旦这条主链路搞清楚，再升级到 JWT、OIDC、SSO 都会容易很多。

---

## 关键设计决策

下面这些选择，几乎决定了你的认证系统会变成什么样。

| 决策点 | 推荐默认值 | 原因 |
| --- | --- | --- |
| 登录状态模型 | Session + HttpOnly Cookie | 最容易做对，撤销简单，适合普通 Web 应用 |
| 密码算法 | Argon2id | 当前通用推荐，抗离线爆破能力强 |
| Session 存储 | 先数据库，后续可切 Redis | MVP 简单，便于理解生命周期 |
| Session 有效期 | 短会话 + 可续期 | 降低长期泄漏风险 |
| Cookie 策略 | `HttpOnly + Secure + SameSite=Lax` | 兼顾安全和可用性 |
| JWT 使用范围 | 服务间 API 或移动端 API | 不要为了“流行”把它塞进一切场景 |
| OAuth2 / OIDC | 需要第三方登录或统一身份时再引入 | 初学阶段先把本地认证做扎实 |
| MFA 方案 | WebAuthn 或 TOTP | 比短信更稳，更抗钓鱼 |

还要特别注意下面几类风险。

### 1. XSS 与 CSRF 不是一回事

- `XSS`：攻击者在你的页面执行脚本
- `CSRF`：攻击者诱导浏览器替你发请求

常见对应策略：

- 抗 XSS：输出转义、CSP、避免把 Token 暴露给前端 JS
- 抗 CSRF：`SameSite`、CSRF Token、双重提交 Cookie、校验来源站点

### 2. JWT 不适合充当“永不过期的登录态”

JWT 最大的问题不是生成，而是撤销。

如果你需要：

- 用户主动退出立即失效
- 管理员强制下线
- 风险设备快速封禁

那就要额外设计黑名单、短 TTL、Refresh Token 轮换等机制。  
否则你得到的只是一枚“很难收回去的凭证”。

### 3. OAuth2 不等于“自己的网站登录”

很多文章会把“Google 登录”统称为 OAuth2 登录，但精确一点应理解为：

- OAuth2 负责授权
- OIDC 负责身份声明

如果你只学了 OAuth2 却没学 OIDC，往往会在 `id_token`、`userinfo`、`nonce`、`issuer` 验证这些地方踩坑。

### 4. 认证错误信息要克制

不要分别返回：

- “用户不存在”
- “密码错误”

这会帮助攻击者做账号枚举。更稳妥的做法是统一返回：

```text
账号或密码错误
```

### 5. 登录成功后要旋转关键状态

至少要考虑：

- 登录成功后旋转 Session ID
- 提权操作后重新认证
- 修改密码后让旧 Session 失效
- 修改邮箱 / MFA 设置时触发二次验证

---

## 一个常见误区清单

- 把密码做一次 `SHA-256` 就当作“加密存储”
- 直接把用户 ID 当 Session ID
- 把 JWT 放进 `localStorage`，却没有认真处理 XSS
- 只做前端“退出登录”，服务端凭证并未撤销
- OAuth 回调里不校验 `state`
- OIDC 登录里不校验 `iss / aud / nonce / exp`
- 用短信验证码就误以为自己已经拥有强 MFA
- 没有限流、没有审计、没有异常登录告警

这些问题单独看都像细节，组合起来就是事故。

---

## 延伸阅读

- Build Your Own X：从项目列表里继续找认证、OAuth、身份系统相关实现思路
- OWASP Authentication Cheat Sheet
- OWASP Session Management Cheat Sheet
- OWASP Password Storage Cheat Sheet
- RFC 7519: JSON Web Token (JWT)
- RFC 6749: The OAuth 2.0 Authorization Framework
- RFC 7636: PKCE for OAuth 2.0
- OpenID Connect Core 1.0
- FIDO2 / WebAuthn 规范与实践指南

如果要继续扩展这个主题，推荐下一步按这个顺序深入：

1. 先把 Session 登录跑通
2. 再补注册、登出、密码重置、邮箱验证
3. 然后实现 JWT access/refresh token 体系
4. 最后再接 OIDC、SSO、MFA、设备管理和风险控制

---

## 今日结论

认证系统的难点从来不只是“验证一次密码”，而是如何把一次身份证明，安全地延续成一条长期可信的请求链路。

对第一个可用系统来说，最稳妥的起点通常不是最“潮”的方案，而是最容易做对的方案：

> 慢哈希密码 + 服务端 Session + 安全 Cookie + 清晰的状态撤销机制

把这条主线真正理解透，后面的 JWT、OAuth2、OIDC、SSO、MFA 才不会只是名词堆叠。
