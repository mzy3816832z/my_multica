import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/apartments',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { public: true, title: '登录', hideTabBar: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/auth/RegisterView.vue'),
      meta: { public: true, title: '注册', hideTabBar: true },
    },
    {
      path: '/forgot-password',
      name: 'ForgotPassword',
      component: () => import('@/views/auth/ForgotPasswordView.vue'),
      meta: { public: true, title: '忘记密码', hideTabBar: true },
    },
    {
      path: '/select-role',
      name: 'SelectRole',
      component: () => import('@/views/auth/SelectRoleView.vue'),
      meta: { public: false, title: '选择身份', hideTabBar: true },
    },
    {
      path: '/apartments',
      name: 'ApartmentList',
      component: () => import('@/views/home/ApartmentListView.vue'),
      meta: { public: true, title: '房源列表' },
    },
    {
      path: '/apartments/:id',
      name: 'ApartmentDetail',
      component: () => import('@/views/apartment/ApartmentDetailView.vue'),
      meta: { public: true, title: '房源详情', hideTabBar: true },
    },
    {
      path: '/room-types/:id',
      name: 'RoomTypeDetail',
      component: () => import('@/views/apartment/RoomTypeDetailView.vue'),
      meta: { public: true, title: '户型详情', hideTabBar: true },
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/views/profile/ProfileView.vue'),
      meta: { public: false, title: '个人中心' },
    },
    {
      path: '/profile/favorites',
      name: 'Favorites',
      component: () => import('@/views/profile/FavoritesView.vue'),
      meta: { public: false, roles: ['tenant'], title: '我的收藏', hideTabBar: true },
    },
    {
      path: '/profile/messages',
      name: 'Messages',
      component: () => import('@/views/profile/MessagesView.vue'),
      meta: { public: false, title: '我的消息', hideTabBar: true },
    },
    {
      path: '/profile/change-password',
      name: 'ChangePassword',
      component: () => import('@/views/profile/ChangePasswordView.vue'),
      meta: { public: false, title: '修改密码', hideTabBar: true },
    },
    {
      path: '/profile/my-apartments',
      name: 'MyApartments',
      component: () => import('@/views/profile/MyApartmentsView.vue'),
      meta: { public: false, roles: ['landlord'], title: '已上架房源', hideTabBar: true },
    },
    {
      path: '/profile/apartments/create',
      name: 'CreateApartment',
      component: () => import('@/views/profile/CreateApartmentView.vue'),
      meta: { public: false, roles: ['landlord'], title: '发布房源', hideTabBar: true },
    },
    {
      path: '/profile/apartments/:id/edit',
      name: 'EditApartment',
      component: () => import('@/views/profile/EditApartmentView.vue'),
      meta: { public: false, roles: ['landlord'], title: '编辑房源', hideTabBar: true },
    },
    {
      path: '/admin/audits',
      name: 'AdminAudits',
      component: () => import('@/views/admin/AuditListView.vue'),
      meta: { public: false, roles: ['admin'], title: '审核管理', hideTabBar: true },
    },
    {
      path: '/admin/audits/:id',
      name: 'AdminAuditDetail',
      component: () => import('@/views/admin/AuditDetailView.vue'),
      meta: { public: false, roles: ['admin'], title: '审核详情', hideTabBar: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { public: true, title: '页面不存在', hideTabBar: true },
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const isPublic = to.meta.public === true
  const requiredRoles = (to.meta.roles as string[] | undefined) || []

  // 设置页面标题
  if (to.meta.title) {
    document.title = to.meta.title as string
  }

  // 未登录且访问非公开页面 → 跳转登录
  if (!isPublic && !authStore.isLoggedIn) {
    showToast('请先登录')
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录但 role 为空 → 强制身份选择（排除身份选择页本身和公开页）
  if (
    authStore.isLoggedIn &&
    !authStore.role &&
    to.path !== '/select-role' &&
    !isPublic
  ) {
    next({ path: '/select-role', query: { redirect: to.fullPath } })
    return
  }

  // 角色权限校验
  if (requiredRoles.length > 0 && !requiredRoles.includes(authStore.role)) {
    showToast('暂无权限访问该页面')
    next({ path: '/' })
    return
  }

  next()
})

export default router
