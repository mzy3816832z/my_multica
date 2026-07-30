import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'

export const useAuthStore = defineStore(
  'auth',
  () => {
    const token = ref<string>('')
    const refreshToken = ref<string>('')
    const userInfo = ref<User | null>(null)

    const isLoggedIn = computed(() => !!token.value)
    const role = computed(() => userInfo.value?.role || '')
    const isAdmin = computed(() => role.value === 'admin')
    const isLandlord = computed(() => role.value === 'landlord')
    const isTenant = computed(() => role.value === 'tenant')

    function setToken(access: string, refresh: string) {
      token.value = access
      refreshToken.value = refresh
    }

    function setUser(user: User) {
      userInfo.value = user
    }

    function logout() {
      token.value = ''
      refreshToken.value = ''
      userInfo.value = null
    }

    return {
      token,
      refreshToken,
      userInfo,
      isLoggedIn,
      role,
      isAdmin,
      isLandlord,
      isTenant,
      setToken,
      setUser,
      logout,
    }
  },
  {
    persist: true,
  }
)
