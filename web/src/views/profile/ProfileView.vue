<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/message'

const router = useRouter()
const authStore = useAuthStore()
const messageStore = useMessageStore()

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    tenant: '租客',
    landlord: '商家',
    admin: '管理员',
  }
  return map[authStore.role] || '用户'
})

const displayName = computed(() => {
  return authStore.userInfo?.phone || authStore.userInfo?.username || '未知用户'
})

// 通用菜单（所有角色）
const commonMenus = [
  { title: '我的消息', path: '/profile/messages', icon: 'comment-o', badge: 'unread' },
  { title: '修改密码', path: '/profile/change-password', icon: 'lock' },
]

// 租客专属菜单
const tenantMenus = [
  { title: '我的收藏', path: '/profile/favorites', icon: 'star-o' },
]

// 商家专属菜单
const landlordMenus = [
  { title: '已上架房源', path: '/profile/my-apartments', icon: 'wap-home-o' },
  { title: '发布房源', path: '/profile/apartments/create', icon: 'plus' },
]

// 管理员专属菜单
const adminMenus = [
  { title: '审核管理', path: '/admin/audits', icon: 'records' },
]

const menus = computed(() => {
  const list = [...commonMenus]
  if (authStore.isTenant) {
    list.unshift(...tenantMenus)
  }
  if (authStore.isLandlord) {
    list.push(...landlordMenus)
  }
  if (authStore.isAdmin) {
    list.push(...adminMenus)
  }
  return list
})

function goPage(path: string) {
  router.push(path)
}

async function handleLogout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出当前账号吗？',
    })
    authStore.logout()
    messageStore.reset()
    router.replace('/login')
  } catch (err: any) {
    if (err?.message === 'cancel') {
      // 用户取消
    }
  }
}
</script>

<template>
  <div class="profile-page">
    <!-- 用户信息卡片 -->
    <div class="bg-white p-4 mb-3">
      <div class="flex items-center">
        <div class="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <van-icon name="user-o" class="text-primary text-2xl" />
        </div>
        <div class="ml-4 flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h2 class="text-lg font-bold text-gray-900 truncate">{{ displayName }}</h2>
            <van-tag type="primary">{{ roleLabel }}</van-tag>
          </div>
          <p class="text-sm text-gray-400 mt-1">ID: {{ authStore.userInfo?.id || '-' }}</p>
        </div>
      </div>
    </div>

    <!-- 菜单列表 -->
    <div class="bg-white">
      <van-cell
        v-for="menu in menus"
        :key="menu.path"
        :title="menu.title"
        is-link
        center
        @click="goPage(menu.path)"
      >
        <template #icon>
          <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center mr-3">
            <van-icon :name="menu.icon" class="text-primary" />
          </div>
        </template>
        <template #value>
          <van-badge v-if="menu.badge === 'unread' && messageStore.hasUnread" :content="messageStore.unreadCount" />
        </template>
      </van-cell>
    </div>

    <!-- 退出登录 -->
    <div class="px-4 mt-6">
      <van-button type="danger" block round plain @click="handleLogout">
        退出登录
      </van-button>
    </div>

    <!-- 底部占位（安全区） -->
    <div class="h-6" />
  </div>
</template>

<style scoped lang="scss">
.profile-page {
  min-height: 100vh;
  background-color: $bg-color;
}
</style>
