# H5 UI 自动化测试

基于 Playwright (Chromium, iPhone 12 移动视口 390x844) 的端到端 UI 测试。

## 前置条件
1. 后端：`cd server && USE_SQLITE=True python manage.py runserver 127.0.0.1:8000`（需先 migrate + 执行 seed_data/seed_script.py）
2. 前端：`cd web && npm run dev`（http://localhost:5173）
3. 测试依赖：`pip install playwright && python -m playwright install chromium`（安装在后端 venv 即可）

## 执行
```bash
server/.venv/Scripts/python test/ui/run_ui_tests.py   # Windows
```

## 说明
- 短信为 mock 模式，测试通过直连 SQLite (`server/db.sqlite3` 的 `verify_codes` 表) 读取验证码完成注册/登录/重置密码流程。
- 测试数据由脚本自动准备：注册租客/商家、商家发布房源、管理员审批上架、租客收藏。
- 报告输出到 `test/report/test_report_YYYYMMDD_HHMMSS.html`，截图存于 `test/report/evidence/`。
