# 上海公寓租赁平台 - 前端

基于 Vue 3 + Vite + TypeScript 的 H5 单页应用。

## 技术栈

- Vue 3.5 + `<script setup>` 组合式 API
- Vite 8
- TypeScript
- Vant 4（移动端 UI）
- Tailwind CSS 3
- Pinia + pinia-plugin-persistedstate
- Vue Router 4
- Axios

## 目录结构

```
src/
├── api/              # 按模块封装的 axios 请求
├── assets/           # 静态资源
├── components/
│   ├── common/       # 通用组件
│   └── business/     # 业务组件
├── views/            # 页面视图
│   ├── auth/         # 登录、注册、忘记密码、身份选择
│   ├── home/         # 房源列表
│   ├── apartment/    # 房源详情、户型详情
│   ├── profile/      # 个人中心、收藏、消息、改密、商家房源
│   └── admin/        # 审核列表、审核详情
├── router/           # 路由配置与权限守卫
├── stores/           # Pinia 状态（auth、ui 等）
├── styles/           # 全局样式、SCSS 变量、Tailwind 入口
├── types/            # TypeScript 类型定义
└── utils/            # 工具函数、请求封装
```

## 启动与构建

```bash
# 安装依赖
npm install

# 开发服务
npm run dev

# 生产构建
npm run build

# 预览构建产物
npm run preview
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 基础路径 | `/api/v1` |

## 响应式基准

以 375px（iPhone 标准宽度）为设计基准，通过 `vw` 函数适配不同屏幕。全局最大宽度限制 480px，居中显示。

## 路由权限

- 公开路由：`/login`、`/register`、`/forgot-password`、`/apartments` 等
- 需登录：个人中心、收藏、消息等
- 需角色：商家路由（`landlord`）、管理员路由（`admin`）
- 路由守卫在 token 失效时自动跳转登录页

## 请求封装

- 统一注入 `Authorization: Bearer <token>`
- 统一解构后端 `{code, message, data}` 响应
- 401 自动清除 token 并跳转登录
- 403/429 全局 toast 提示

## 全局能力

- **Loading**：通过 `uiStore.showLoading()` / `hideLoading()` 控制
- **Toast**：直接使用 Vant `showToast()`
- **Pinia 持久化**：`authStore` 自动持久化到 localStorage
