<script setup lang="ts">
import { ref, reactive, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { changePassword, sendSmsCode } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  newPassword: '',
  confirmPassword: '',
  smsCode: '',
})

const loading = ref(false)
const smsCountdown = ref(0)
const smsTimer = ref<ReturnType<typeof setInterval> | null>(null)

const phone = computed(() => authStore.userInfo?.phone || '')
const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(phone.value))
const canSendSms = computed(() => phoneValid.value && smsCountdown.value === 0)

const canSubmit = computed(() => {
  if (!form.smsCode || form.smsCode.length !== 6) return false
  if (!form.newPassword || form.newPassword.length < 6) return false
  if (form.newPassword !== form.confirmPassword) return false
  return true
})

async function handleSendSms() {
  if (!canSendSms.value) return
  try {
    await sendSmsCode(phone.value, 'change_password')
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
    await changePassword({
      sms_code: form.smsCode,
      new_password: form.newPassword,
    })
    showToast('密码修改成功，请重新登录')
    authStore.logout()
    router.replace('/login')
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="change-password-page">
    <!-- 顶部导航栏 -->
    <van-nav-bar title="修改密码" left-arrow fixed placeholder @click-left="router.back" />

    <div class="px-4 pt-4">
      <van-form @submit="onSubmit">
        <!-- 手机号（只读展示） -->
        <van-field
          :model-value="phone"
          label="手机号"
          readonly
          placeholder="未绑定手机号"
          class="mb-3"
        />

        <!-- 验证码 -->
        <van-field
          v-model="form.smsCode"
          type="digit"
          maxlength="6"
          label="验证码"
          placeholder="请输入短信验证码"
          :rules="[
            { required: true, message: '请输入验证码' },
            { pattern: /^\d{6}$/, message: '验证码为6位数字' },
          ]"
          class="mb-3"
        >
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
          label="新密码"
          placeholder="请输入新密码（至少6位）"
          :rules="[
            { required: true, message: '请输入新密码' },
            { pattern: /^.{6,}$/, message: '密码至少6位' },
          ]"
          class="mb-3"
        />

        <!-- 确认密码 -->
        <van-field
          v-model="form.confirmPassword"
          type="password"
          label="确认密码"
          placeholder="请再次输入新密码"
          :rules="[
            { required: true, message: '请确认密码' },
            {
              validator: () => form.newPassword === form.confirmPassword,
              message: '两次输入的密码不一致',
            },
          ]"
          class="mb-3"
        />

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
          确认修改
        </van-button>
      </van-form>
    </div>
  </div>
</template>

<style scoped lang="scss">
.change-password-page {
  min-height: 100vh;
  background-color: $bg-color;
}
</style>
