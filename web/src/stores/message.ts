import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMessages, markMessageRead, getUnreadCount } from '@/api/message'
import type { Message } from '@/types'

export const useMessageStore = defineStore('message', () => {
  const messages = ref<Message[]>([])
  const unreadCount = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const total = ref(0)
  const loading = ref(false)
  const finished = ref(false)

  const hasUnread = computed(() => unreadCount.value > 0)

  async function fetchMessages(isRefresh = false) {
    if (loading.value) return
    loading.value = true
    try {
      const currentPage = isRefresh ? 1 : page.value
      const data = await getMessages({ page: currentPage, page_size: pageSize.value })
      if (isRefresh) {
        messages.value = data.items
        page.value = 1
      } else {
        messages.value.push(...data.items)
      }
      total.value = data.total
      finished.value = messages.value.length >= data.total
      if (!isRefresh) {
        page.value++
      }
    } catch {
      // 错误已在 request 拦截器中 toast
    } finally {
      loading.value = false
    }
  }

  async function readMessage(id: number) {
    const msg = messages.value.find((m) => m.id === id)
    if (!msg) return
    if (msg.is_read) return
    try {
      await markMessageRead(id)
      msg.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // 错误已在 request 拦截器中 toast
    }
  }

  async function fetchUnreadCount() {
    try {
      const res = await getUnreadCount()
      unreadCount.value = res.unread_count
    } catch {
      // 静默失败
    }
  }

  function reset() {
    messages.value = []
    unreadCount.value = 0
    page.value = 1
    total.value = 0
    finished.value = false
  }

  return {
    messages,
    unreadCount,
    hasUnread,
    loading,
    finished,
    fetchMessages,
    readMessage,
    fetchUnreadCount,
    reset,
  }
})
