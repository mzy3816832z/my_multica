<script setup lang="ts">
import { ref, reactive, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { sendSmsCode, resetPassword } from '@/api/auth'

const router = useRouter()

const form = reactive({
  phone: '',
  smsCode: '',
  newPassword: '',
  confirmPassword: '',
})

const loading = ref(false)
const smsCountdown = ref(0)
const smsTimer = ref<ReturnType<typeof setInterval> | null>(null)

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))
const canSendSms = computed(() => phoneValid.value && smsCountdown.value === 0)

const canSubmit = computed(() => {
  if (!phoneValid.value) return false
  if (form.smsCode.length !== 6) return false
  if (form.newPassword.length < 6) return false
  if (form.newPassword !== form.confirmPassword) return false
  return true
})

async function handleSendSms() {
  if (!canSendSms.value) return
  try {
    await sendSmsCode(form.phone, 'reset_password')
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

async function onSubmit() {
  if (!canSubmit.value) return
  loading.value = true
  try {
    await resetPassword({
      phone: form.phone,
      sms_code: form.smsCode,
      new_password: form.newPassword,
    })
    // 重置成功后跳转登录
    router.replace('/login')
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
    <div class="flex items-center px-4 pt-4 pb-2">
      <van-icon name="arrow-left" class="text-xl text-gray-700" @click="router.back()" />
      <h1 class="flex-1 text-center text-lg font-bold">忘记密码</h1>
      <span class="w-6" />
    </div>

    <div class="px-6 flex-1">
      <p class="text-sm text-gray-400 mb-6 mt-2">验证手机号后重置密码</p>

      <van-form @submit="onSubmit">
        <!-- 手机号 -->
        <van-field
          v-model="form.phone"
          type="tel"
          maxlength="11"
          placeholder="请输入手机号"
          :rules="[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误' }]"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="phone-o" class="text-gray-400 mr-2" />
          </template>
        </van-field>

        <!-- 验证码 -->
        <van-field
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

        <!-- 新密码 -->
        <van-field
          v-model="form.newPassword"
          type="password"
          placeholder="请设置新密码（至少6位）"
          :rules="[{ required: true, message: '请输入新密码' }]"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="lock" class="text-gray-400 mr-2" />
          </template>
        </van-field>

        <!-- 确认密码 -->
        <van-field
          v-model="form.confirmPassword"
          type="password"
          placeholder="请再次输入新密码"
          :rules="[
            { required: true, message: '请确认密码' },
            { validator: (val: string) => val === form.newPassword, message: '两次密码不一致' },
          ]"
          class="mb-3"
        >
          <template #left-icon>
            <van-icon name="lock" class="text-gray-400 mr-2" />
          </template>
        </van-field>

        <!-- 提交按钮 -->
        <van-button
          type="primary"
          block
          round
          :loading="loading"
          :disabled="!canSubmit"
          native-type="submit"
          class="mt-6"
        >
          重置密码
        </van-button>
      </van-form>

      <!-- 底部 -->
      <div class="mt-4 text-center text-sm">
        <span class="text-gray-500">想起密码了？</span>
        <router-link to="/login" class="text-primary">去登录</router-link>
      </div>
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
