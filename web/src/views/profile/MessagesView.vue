<script setup lang="ts">
import { formatFriendlyTime } from '@/utils/datetime'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessageStore } from '@/stores/message'
import type { Message } from '@/types'

const router = useRouter()
const messageStore = useMessageStore()

const refreshing = ref(false)

function onLoad() {
  messageStore.fetchMessages()
}

function onRefresh() {
  messageStore.finished = false
  messageStore.fetchMessages(true)
  refreshing.value = false
}

function handleClickMessage(msg: Message) {
  messageStore.readMessage(msg.id)
  // 可扩展：点击后跳转到关联房源或审核详情
  // router.push('/apartments/' + msg.related_apartment_id)
}

function formatTime(time: number) {
  return formatFriendlyTime(time)
}

onMounted(() => {
  messageStore.fetchMessages(true)
  messageStore.fetchUnreadCount()
})
</script>

<template>
  <div class="messages-page">
    <!-- 顶部导航栏 -->
    <van-nav-bar title="我的消息" left-arrow fixed placeholder @click-left="router.back">
      <template #right>
        <span v-if="messageStore.hasUnread" class="text-sm text-primary" @click="messageStore.fetchMessages(true); messageStore.fetchUnreadCount()">
          刷新
        </span>
      </template>
    </van-nav-bar>

    <!-- 列表内容 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="messageStore.loading"
        :finished="messageStore.finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="messageStore.messages.length === 0 && !messageStore.loading" class="empty-state">
          <van-empty description="暂无消息" />
        </div>

        <div class="px-3 py-2 space-y-2">
          <div
            v-for="msg in messageStore.messages"
            :key="msg.id"
            class="bg-white rounded-xl p-4 shadow-sm relative"
            :class="{ 'bg-primary/5': !msg.is_read }"
            @click="handleClickMessage(msg)"
          >
            <!-- 未读红点 -->
            <div v-if="!msg.is_read" class="absolute top-3 right-3 w-2 h-2 rounded-full bg-danger" />

            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-bold text-gray-900 pr-4">{{ msg.title }}</h3>
              <span class="text-xs text-gray-400 flex-shrink-0">{{ formatTime(msg.created_at) }}</span>
            </div>
            <p class="text-sm text-gray-600 leading-relaxed">{{ msg.content }}</p>
            <div class="mt-2 flex items-center gap-2">
              <van-tag v-if="msg.type === 'first_rejected'" type="danger">首次审核驳回</van-tag>
              <van-tag v-else-if="msg.type === 'change_rejected'" type="warning">变更审核驳回</van-tag>
              <span v-if="msg.is_read" class="text-xs text-gray-400">已读</span>
              <span v-else class="text-xs text-primary">未读</span>
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<style scoped lang="scss">
.messages-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.empty-state {
  padding-top: 20vh;
}

.bg-primary\/5 {
  background-color: rgba(var(--van-primary-color-rgb), 0.05);
}

.bg-danger {
  background-color: $danger;
}
</style>
