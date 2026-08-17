# H5 UI 自动化测试

基于 Playwright (Chromium, iPhone 12 移动视口 390x844) 的端到端 UI 测试。

## 推荐：一键脚本（起服务 → 就绪探测 → 跑测试 → 收尾）

```powershell
powershell -ExecutionPolicy Bypass -File test\ui\run_env.ps1
```

脚本自动完成：端口预检 → 后台起后端(SQLite, `--noreload`) + 前端(Vite) → 就绪探测 → 前台阻塞跑 `run_ui_tests.py` → 杀掉两个服务。**后台启动 + 前台阻塞跑测试 + 同一轮内收尾**，避免长驻服务在前台卡住不返回。端口默认后端 `8001`、前端 `5174`，刻意避开常见的本地开发环境(8000/5173)；可用 `TEST_BACKEND_PORT` / `TEST_FRONTEND_PORT` 覆盖。

### 前置（一次性）

1. 后端依赖已装：`server\.venv` 或 `server\venv`
2. 前端依赖已装：`web\node_modules`
3. `USE_SQLITE=True` 下完成 migrate + 种子数据：

```powershell
cd server
$env:USE_SQLITE = 'True'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe seed_data\seed_script.py
cd ..
```

### 端口约定（三处必须对齐）

| 环节 | 配置项 | 值 |
|---|---|---|
| 后端 | `runserver` | `127.0.0.1:8001`（脚本内 `$BackendPort`） |
| 前端 Vite | `VITE_API_TARGET` | `http://127.0.0.1:8001`（`/api`、`/uploads` 代理目标） |
| 前端 Vite | `VITE_PORT` | `5174`（脚本内 `$FrontendPort`） |
| 测试脚本 | `UI_BASE_URL` | `http://localhost:5174` |

> 三处由 `run_env.ps1` 自动保持一致；若手动改端口，务必同时改 `TEST_BACKEND_PORT` / `TEST_FRONTEND_PORT`。

## 手动执行（不推荐，易因前台起服务而卡住）

### 前置条件
1. 后端：`cd server && USE_SQLITE=True python manage.py runserver 127.0.0.1:8000`（需先 migrate + 执行 seed_data/seed_script.py）
2. 前端：`cd web && npm run dev`（http://localhost:5173）
3. 测试依赖：`pip install playwright && python -m playwright install chromium`（安装在后端 venv 即可）

### 执行
```bash
server/.venv/Scripts/python test/ui/run_ui_tests.py   # Windows
```

## 说明
- 短信为 mock 模式，测试通过直连 SQLite (`server/db.sqlite3` 的 `verify_codes` 表) 读取验证码完成注册/登录/重置密码流程。
- 测试数据由脚本自动准备：注册租客/商家、商家发布房源、管理员审批上架、租客收藏。
- 报告输出到 `test/report/test_report_YYYYMMDD_HHMMSS.html`，截图存于 `test/report/evidence/`。
