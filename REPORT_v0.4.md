# 启航编程管理系统 · v0.4 交付报告

> 课题：接手 `training-platform` 项目，完成**四类身份登录**（员工 / 教师 / 学员 / 家长）、**身份区分**与**数据库接入**，并补齐自动化测试。
> 时间：2026-06 · 作者：Senior Developer（接手开发）

---

## 1. 任务背景与目标

原项目（`Yi-forever/training-platform`）已具备第三阶段前后端一体化能力，但存在两块关键缺口：

1. **存储停留在 JSON 单文件**（`data/app.json`），无关系数据库，难以支撑多身份、多表的真实业务；
2. **仅支持员工（后台管理）登录**，缺少教师 / 学员 / 家长三类用户门户，身份区分不清晰。

本次目标（用户明确授权"按最优方案直接执行，无需确认"）：

- 实现 **老师 / 学生 / 家长账户登录**，并与员工登录**清晰区分不同身份**；
- **接入数据库**（替换 JSON 文件存储）；
- **编写测试**；
- 交付**本报告**。

---

## 2. 原项目分析

| 维度 | 原实现 |
| --- | --- |
| 后端 | FastAPI，分层 `api → services → db` |
| 存储 | `JsonDB` 单 JSON 文件，软删（`deletedAt`）、`next_code` 业务取号、事务快照 |
| 认证 | JWT（自研 Bearer）+ PBKDF2-SHA256 密码哈希 |
| 账号 | 仅 `users` 集合，账号即员工，无教师/学员/家长门户概念 |
| 前端 | 原生 HTML/CSS/JS，同源托管，登录页仅填账号密码 |

接手要点：**业务逻辑（课程/班级/缴费/统计/删除保护）已较完整**，因此本次以"最小侵入、接口兼容"为原则重构存储与认证，避免重写既有 service/api。

---

## 3. 本次交付内容

### 3.1 数据库接入（替换 JSON）
- 引入 **SQLAlchemy 2.0 ORM**，默认 **SQLite**（`data/app.db`），零配置即可运行；
- 通过环境变量 **`QIHANG_DB_URL`** 一键切换 MySQL（`mysql+pymysql://...`），业务代码无需改动；
- 抽象出**接口兼容的仓储层 `DB`**（`app/db/repository.py`）：`alive / find / locate / insert / update_fields / soft_delete / next_code / transaction` 等方法签名与原 `JsonDB` 完全一致，service / api 层仅需改 import 即完成切换；
- 表结构与原 JSON 字典**键名一一对应**（如 `courseId`、`parentPhone`、`startDate`），实现行 ↔ 字典零成本互转；
- 修复 SQLite 默认连接池的**跨会话提交不可见**问题（改用 `StaticPool`）。

### 3.2 四类身份登录与区分
- 统一 `accounts` 表，以 `identity` 字段区分四类身份：`staff`（员工）/ `teacher`（教师）/ `student`（学员）/ `parent`（家长）；
- **统一登录入口** `POST /api/v1/auth/login`，支持**用户名或手机号**登录；家长手机号登录时优先命中家长身份（避免与员工/教师共用号码冲突，例如 `13957100001`）；
- 新增 **`GET /api/v1/auth/context`** 身份专属工作台：
  - 员工：管理概览（无门户专属字段）；
  - 教师：所带班级列表 + 学员总数；
  - 学员：我的班级 / 课程 / 带班教师 / 已缴总额；
  - 家长：关联学员动态列表；
- 登录响应与 `get_current_user` 均携带 `identity / role / refId`，后续接口可按身份做门禁（`require_identity`）。

### 3.3 前端身份选择
- 登录页 `web/login.html` 新增**「员工 / 教师 / 学员 / 家长」四门户切换**，切换时自动填充对应演示账号并展示该身份的工作台说明，让"身份区分"在 UI 上清晰可见。

### 3.4 种子数据
- `app/db/seed.py` 重写：5 个员工账号、7 个教师门户账号（工号 `JSxxx`）、16 个学员门户账号（`XSxxx`）、按"家长+电话"去重生成的家长账号（`P001…`）+ 学员—家长关联，以及教师/课程/班级/学员/缴费/新闻/资源等业务实体。

---

### 3.5 身份门禁与服务端隔离（接续修复）

初版虽已打通四类身份登录，但所有管理类接口仅做"是否登录"校验，**非员工身份（教师/学员/家长）登录后仍可调取、改写全量后台数据——存在越权**。本轮修复将其真正闭环：

- **管理后台接口收归 `require_admin`**：`students / classes / courses / payments / teachers / dashboard` 的全部端点（含 GET 列表与写操作）统一要求员工（超级管理员）身份，非员工访问返回 **403**；`news / resources` 的**读接口**保留全员可见（机构资讯门户），但**写操作**（发布/编辑/删除/上传）同样收归 `require_admin`。
- **身份专属接口落地 `require_identity` 门禁**：新增 `app/api/portal.py`，提供 `/portal/overview` 及 `/portal/teacher/classes`、`/portal/student/profile`、`/portal/parent/children`，以 `require_teacher / require_student / require_parent` 包装依赖显式门禁，越权访问返回 403；`AccountContextService.build` 复用于保证与 `/auth/context` 数据一致。
- **前端按身份分流**：登录后员工进入 `dashboard.html`，教师/学员/家长进入新建的 `portal.html`（按身份渲染专属工作台）；`common.js` 的 `boot` 对后台页面做员工守卫（非员工访问自动跳转门户），`hydrate` 按身份跳过受限集合，避免无谓 403。

> 该修复不破坏既有回归：`scripts/verify_api.py` 全程使用超级管理员 token，管理接口 94/94 全通过；pytest 新增 5 项门禁/分流断言，合计 **18/18** 通过。

## 4. 关键文件清单

| 文件 | 职责 |
| --- | --- |
| `app/db/session.py` | 引擎/会话（`StaticPool`）、`init_db` / `reset_schema` |
| `app/db/models.py` | ORM 模型（`Account` + 8 张业务表 + `StudentParent` 关联表） |
| `app/db/repository.py` | 接口兼容仓储层（`DB`）、`find_account`、`soft_delete_student_cascade` 等 |
| `app/db/seed.py` | 种子数据（四类身份账号 + 业务实体） |
| `app/core/deps.py` | `get_current_user` / `require_admin` / `require_identity` |
| `app/services/people.py` | `AuthService.login`、`AccountContextService.build`（身份专属工作台） |
| `app/api/auth.py` | 登录 / `me` / `context` / 改密码 / 改资料 |
| `app/main.py` | 启动钩子：建表 + 空库播种 |
| `web/login.html` | 四门户身份切换登录页 |
| `tests/test_identities.py` | pytest：四类身份登录 / 门禁 / 数据库 CRUD / 级联删除 |
| `scripts/verify_api.py` | 94 项 API 冒烟断言（兼容回归） |

---

## 5. 测试情况

| 测试 | 命令 | 结果 |
| --- | --- | --- |
| API 冒烟回归 | `python3.11 scripts/verify_api.py` | **94 / 94 通过** |
| 身份与数据库单测 | `python3.11 -m pytest tests/ -q` | **13 / 13 通过** |

测试覆盖：四类身份登录、手机号登录、错误密码 401、禁用账号 403、缺令牌 401、`/auth/context` 身份差异化、身份门禁 `require_identity`、数据库增删改查生命周期、学员删除级联软删缴费（404）、缴费作废统计口径。

---

## 6. 如何运行

```bash
# 安装依赖（已预装 sqlalchemy / pytest）
pip install -e .

# 启动（默认 SQLite，首次自动建表 + 播种）
python3.11 -m uvicorn app.main:app --reload --port 8000
# 浏览器访问 http://127.0.0.1:8000  →  登录页可选择四类身份门户

# 运行测试
python3.11 scripts/verify_api.py
python3.11 -m pytest tests/ -q
```

四大演示账号：

| 身份 | 账号 | 密码 |
| --- | --- | --- |
| 员工（超级管理员） | `admin` | `admin123` |
| 教师 | `JS001` | `123456` |
| 学员 | `XS001` | `123456` |
| 家长（也可手机号 `15868710001` 登录） | `P001` | `123456` |

---

## 7. 已知限制与后续建议

**已知限制**
- 令牌为自研轻量 Bearer（HMAC-SHA256），正式生产建议替换为 PyJWT（接口形状已对齐，改动极小）；
- 教师/学员/家长专属门户目前以只读工作台为主（展示所带班级、我的学籍与缴费、关联学员）；审批/互动类写操作尚未开放给非员工（符合"管理后台仅员工"的定位）。

**后续建议**
1. 为教师/学员/家长分别落地专属路由与页面（用 `require_identity` 做服务端门禁）；
2. 接入 MySQL + Redis（`QIHANG_DB_URL` 已预留），并补充 Alembic 迁移；
3. 补充分页/权限的端到端测试与 CI。

---

## 8. 前端体验优化（Design Taste Plus 技能）

使用 `design-taste-plus` 技能对全部前端界面做了一次反模板（anti-slop）重构，遵循其方法论：先读 brief → 选诚实设计基底 → 设调性旋钮 → 编辑器式构建 → 过 preflight 闸门。

**设计判读**：培训机构运营控制台 + 教师/学员/家长三类门户，采用 **control-center（控制中枢）** 审美，单一自信蓝色强调色 + 柔和中性画布。

**调性旋钮**：`DESIGN_VARIANCE=7` · `MOTION_INTENSITY=5` · `VISUAL_DENSITY=6`。

**主要改动**
- `web/css/style.css` 全量重写：统一蓝色强调色（移除原有的 AI 紫渐变 `#4f46e5→#7c3aed→#a855f7`）、暗色精修侧边栏（激活指示条）、柔和分层阴影、一致圆角系统、移动端 `100dvh`、进度条改用 `transform: scaleX` 动画；新增 `page-head / identity-pill / empty-state / skeleton / reveal` 组件与 `prefers-reduced-motion` 降级。
- `web/js/common.js`：顶栏新增身份徽章（员工/教师/学员/家长四色），新增 `pageHead() / emptyState() / skeleton()` 复用函数。
- `web/login.html`：改为品牌分栏式（左侧叙事 + 右侧表单），保留四身份切换与登录分流。
- `web/portal.html` / `web/dashboard.html`：启用 `page-head` 与 `reveal` 入场动效、空状态组件。
- 为 courses / classes / teachers / students / payments / news / resources / users / settings / profile 共 10 个页面补齐统一 `page-head` 标题区。

**静态审计（audit_frontend_static.py）**：结构性反模板问题（AI 紫渐变、100vh、width 动画）**全部清零**；可见 HTML em-dash 残留为 **0**；剩余 43 处 em-dash 仅在 JS 注释中（不可见，不影响交付质量）。JS 语法校验 13/13 通过。

**集成验证**：`uvicorn` 启动后登录页/CSS/门户/工作台/JS 均返回 200，登录链路 `identity=staff` 正常。
