<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { selectRole } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const selected = ref<'tenant' | 'landlord' | null>(null)
const loading = ref(false)

const roles = [
  {
    key: 'tenant' as const,
    title: '我是租客',
    desc: '寻找心仪的公寓房源',
    icon: 'search',
    color: '#1989fa',
  },
  {
    key: 'landlord' as const,
    title: '我是商家',
    desc: '发布和管理公寓房源',
    icon: 'shop-o',
    color: '#07c160',
  },
]

async function onConfirm() {
  if (!selected.value) return
  loading.value = true
  try {
    const user = await selectRole(selected.value)
    authStore.setUser(user)

    const redirect = route.query.redirect as string
    router.replace(redirect || '/apartments')
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-white">
    <!-- 顶部 -->
    <div class="px-6 pt-12 pb-4">
      <h1 class="text-xl font-bold text-gray-900">选择您的身份</h1>
      <p class="text-sm text-gray-400 mt-1">选择后将无法修改，请谨慎选择</p>
    </div>

    <!-- 选项卡片 -->
    <div class="px-6 flex-1 space-y-4 mt-4">
      <div
        v-for="role in roles"
        :key="role.key"
        class="relative flex items-center p-5 rounded-xl border-2 transition-all cursor-pointer"
        :class="selected === role.key ? 'border-primary bg-blue-50' : 'border-gray-100 bg-gray-50'"
        @click="selected = role.key"
      >
        <!-- 选中标记 -->
        <div
          v-if="selected === role.key"
          class="absolute top-3 right-3 w-5 h-5 rounded-full bg-primary flex items-center justify-center"
        >
          <van-icon name="success" class="text-white text-xs" />
        </div>

        <!-- 图标 -->
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center mr-4"
          :style="{ backgroundColor: role.color + '15' }"
        >
          <van-icon :name="role.icon" class="text-xl" :style="{ color: role.color }" />
        </div>

        <!-- 文字 -->
        <div>
          <h3 class="text-base font-bold text-gray-900">{{ role.title }}</h3>
          <p class="text-sm text-gray-400 mt-0.5">{{ role.desc }}</p>
        </div>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="px-6 py-6">
      <van-button
        type="primary"
        block
        round
        :loading="loading"
        :disabled="!selected"
        @click="onConfirm"
      >
        确认选择
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.border-primary {
  border-color: #1989fa;
}
.bg-blue-50 {
  background-color: #f0f9ff;
}
.bg-primary {
  background-color: #1989fa;
}
</style>
