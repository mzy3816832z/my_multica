<script setup lang="ts">
import { ref, reactive, computed, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { loginByPassword, loginByCode, sendSmsCode } from '@/api/auth'
import type { LoginResult } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 登录模式切换
const mode = ref<'password' | 'code'>('password')

const form = reactive({
  phone: '',
  password: '',
  smsCode: '',
})

const loading = ref(false)
const smsCountdown = ref(0)
const smsTimer = ref<ReturnType<typeof setInterval> | null>(null)

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))
const canSendSms = computed(() => phoneValid.value && smsCountdown.value === 0)
const phoneRules = computed(() => {
  if (mode.value === 'code') {
    return [
      { required: true, message: '请输入手机号' },
      { pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误' },
    ]
  }
  return [{ required: true, message: '请输入账号' }]
})
const canSubmit = computed(() => {
  if (mode.value === 'password') {
    return form.phone.trim().length > 0 && form.password.length >= 6
  }
  if (!phoneValid.value) return false
  return form.smsCode.length === 6
})

async function handleSendSms() {
  if (!canSendSms.value) return
  try {
    await sendSmsCode(form.phone, 'login')
    smsCountdown.value = 60
    smsTimer.value = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0 && smsTimer.value) {
        clearInterval(smsTimer.value)
        smsTimer.value = null
      }
    }, 1000)
  } catch {
    // 错误已在 request 拦截器中 toast
  }
}

onUnmounted(() => {
  if (smsTimer.value) {
    clearInterval(smsTimer.value)
    smsTimer.value = null
  }
})

function handleLoginSuccess(res: LoginResult) {
  authStore.setToken(res.access_token, res.refresh_token)
  authStore.setUser(res.user)

  // 管理员登录后直接跳转审核管理
  if (res.user.role === 'admin') {
    router.replace('/admin/audits')
    return
  }

  // 首次登录无角色 → 强制身份选择
  if (!res.user.role) {
    const redirect = route.query.redirect as string
    router.replace({ path: '/select-role', query: redirect ? { redirect } : undefined })
    return
  }

  const redirect = route.query.redirect as string
  router.replace(redirect || '/apartments')
}

async function onSubmit() {
  if (!canSubmit.value) return
  loading.value = true
  try {
    let res: LoginResult
    if (mode.value === 'password') {
      res = await loginByPassword({ username: form.phone, password: form.password })
    } else {
      res = await loginByCode({ phone: form.phone, sms_code: form.smsCode })
    }
    handleLoginSuccess(res)
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-white">
    <!-- 顶部品牌区 -->
    <div class="flex flex-col items-center justify-center pt-12 pb-8">
      <div class="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center mb-4">
        <van-icon name="wap-home-o" class="text-white text-3xl" />
      </div>
      <h1 class="text-xl font-bold text-gray-900">上海公寓租赁</h1>
      <p class="text-sm text-gray-400 mt-1">发现理想居所</p>
    </div>

    <!-- 登录表单 -->
    <div class="px-6 flex-1">
      <!-- 模式切换 -->
      <div class="flex mb-6 bg-gray-100 rounded-lg p-1">
        <button
          class="flex-1 py-2 text-sm font-medium rounded-md transition-colors"
          :class="mode === 'password' ? 'bg-white text-primary shadow-sm' : 'text-gray-500'"
          @click="mode = 'password'"
        >
          密码登录
        </button>
        <button
          class="flex-1 py-2 text-sm font-medium rounded-md transition-colors"
          :class="mode === 'code' ? 'bg-white text-primary shadow-sm' : 'text-gray-500'"
          @click="mode = 'code'"
        >
          验证码登录
        </button>
      </div>

      <van-form @submit="onSubmit">
        <!-- 账号 -->
        <van-field
          v-model="form.phone"
          :placeholder="mode === 'password' ? '请输入手机号或管理员账号' : '请输入手机号'"
          :rules="phoneRules"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="phone-o" class="text-gray-400 mr-2" />
          </template>
        </van-field>

        <!-- 密码 -->
        <van-field
          v-if="mode === 'password'"
          v-model="form.password"
          type="password"
          placeholder="请输入密码"
          :rules="[{ required: true, message: '请输入密码' }]"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="lock" class="text-gray-400 mr-2" />
          </template>
        </van-field>

        <!-- 验证码 -->
        <van-field
          v-if="mode === 'code'"
          v-model="form.smsCode"
          type="digit"
          maxlength="6"
          placeholder="请输入验证码"
          :rules="[{ required: true, message: '请输入验证码' }]"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="comment-o" class="text-gray-400 mr-2" />
          </template>
          <template #button>
            <van-button
              size="small"
              type="primary"
              plain
              :disabled="!canSendSms"
              @click="handleSendSms"
            >
              {{ smsCountdown > 0 ? `${smsCountdown}s后重发` : '获取验证码' }}
            </van-button>
          </template>
        </van-field>

        <!-- 登录按钮 -->
        <van-button
          type="primary"
          block
          round
          :loading="loading"
          :disabled="!canSubmit"
          native-type="submit"
          class="mt-6"
        >
          登录
        </van-button>
      </van-form>

      <!-- 底部操作 -->
      <div class="flex justify-between mt-4 text-sm">
        <router-link to="/forgot-password" class="text-gray-500">忘记密码？</router-link>
        <router-link to="/register" class="text-primary">去注册</router-link>
      </div>
    </div>

    <!-- 底部协议 -->
    <div class="px-6 py-4 text-center text-xs text-gray-400">
      登录即代表同意
      <span class="text-primary">用户协议</span>
      和
      <span class="text-primary">隐私政策</span>
    </div>
  </div>
</template>

<style scoped>
:deep(.van-field) {
  background-color: #f7f8fa;
  border-radius: 8px;
}
:deep(.van-field__control) {
  font-size: 15px;
}
</style>
