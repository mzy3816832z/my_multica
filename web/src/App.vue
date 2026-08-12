<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()

const showTabBar = computed(() => {
  return authStore.isLoggedIn && !!authStore.role && !route.meta.hideTabBar
})

const activeTab = computed(() => {
  const path = route.path
  if (path.startsWith('/profile')) return 'profile'
  return 'apartments'
})

function goAdmin() {
  router.push('/admin/audits')
}
</script>

<template>
  <div class="app-wrapper" :class="{ 'has-tabbar': showTabBar }">
    <!-- 桌面端顶部导航栏 -->
    <div v-if="showTabBar" class="desktop-navbar">
      <div class="desktop-navbar-inner">
        <span class="navbar-brand" @click="router.push('/apartments')">上海公寓租赁</span>
        <div class="navbar-links">
          <span
            :class="['navbar-link', { active: activeTab === 'apartments' }]"
            @click="router.push('/apartments')"
          >房源</span>
          <span
            :class="['navbar-link', { active: activeTab === 'profile' }]"
            @click="router.push('/profile')"
          >我的</span>
          <span
            v-if="authStore.isAdmin"
            class="navbar-link"
            @click="goAdmin"
          >审核管理</span>
        </div>
      </div>
    </div>

    <RouterView />

    <!-- 底部 TabBar（仅移动端显示） -->
    <div class="mobile-tabbar">
      <van-tabbar
        v-if="showTabBar"
        v-model="activeTab"
        :safe-area-inset-bottom="true"
        route
        fixed
        placeholder
      >
        <van-tabbar-item icon="home-o" to="/apartments">房源</van-tabbar-item>
        <van-tabbar-item icon="user-o" to="/profile">我的</van-tabbar-item>
      </van-tabbar>
    </div>

    <!-- 全局 Loading -->
    <van-overlay :show="uiStore.loading" :z-index="2000" class="global-loading" lock-scroll>
      <div class="loading-content">
        <van-loading :text="uiStore.loadingText" vertical color="#fff" text-color="#fff" />
      </div>
    </van-overlay>
  </div>
</template>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  background-color: #f7f8fa;
}

.desktop-navbar {
  display: none;
}

.desktop-navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
}

.navbar-brand {
  font-size: 18px;
  font-weight: 700;
  color: #323233;
  cursor: pointer;
}

.navbar-links {
  display: flex;
  gap: 24px;
}

.navbar-link {
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.navbar-link:hover {
  color: #1989fa;
}

.navbar-link.active {
  color: #1989fa;
  border-bottom-color: #1989fa;
}

.mobile-tabbar {
  display: block;
}

@media (min-width: 768px) {
  .desktop-navbar {
    display: block;
    position: sticky;
    top: 0;
    z-index: 100;
    background-color: #fff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  .mobile-tabbar {
    display: none;
  }
}

.global-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
