<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { BrowseHistoryItem } from '@/types'

const HISTORY_KEY = 'browse_history'
const router = useRouter()

const list = ref<BrowseHistoryItem[]>([])
const refreshing = ref(false)

function loadHistory(): BrowseHistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const data = JSON.parse(raw) as BrowseHistoryItem[]
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

function refreshList() {
  list.value = loadHistory()
}

function goDetail(id: number) {
  router.push('/apartments/' + id)
}

function onRefresh() {
  refreshing.value = true
  refreshList()
  refreshing.value = false
}

function handleClear() {
  list.value = []
  localStorage.removeItem(HISTORY_KEY)
}

function goBack() {
  router.back()
}

onMounted(() => {
  refreshList()
})
</script>

<template>
  <div class="history-page">
    <van-nav-bar title="浏览历史" left-arrow fixed placeholder @click-left="goBack" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div v-if="list.length === 0" class="empty-state">
        <van-empty description="暂无浏览记录" />
      </div>

      <template v-else>
        <div class="history-header px-4 py-2">
          <span class="text-sm text-gray-400">{{ list.length }} 条记录</span>
          <span class="text-sm text-danger underline" @click="handleClear">清空</span>
        </div>

        <div class="history-grid px-3 py-2">
          <div
            v-for="item in list"
            :key="item.apartment_id"
            class="history-card bg-white rounded-xl overflow-hidden shadow-sm"
            @click="goDetail(item.apartment_id)"
          >
            <div class="card-cover bg-gray-100">
              <van-image
                :src="item.cover_image"
                fit="cover"
                class="w-full h-full"
                :alt="item.name"
              />
              <div class="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                ¥{{ item.min_monthly_rent || '?' }}/月起
              </div>
            </div>
            <div class="p-3">
              <h3 class="text-base font-bold text-gray-900 line-clamp-1">{{ item.name }}</h3>
              <p class="text-sm text-gray-500 mt-1 flex items-center">
                <van-icon name="location-o" class="mr-1" />
                {{ item.district_name || '' }} {{ item.street_name || '' }}
              </p>
            </div>
          </div>
        </div>
      </template>
    </van-pull-refresh>
  </div>
</template>

<style scoped lang="scss">
.history-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.history-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-cover {
  height: 176px;
}

@media (min-width: 768px) {
  .history-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    padding: 16px 24px !important;
    max-width: 1200px;
    margin: 0 auto;
  }

  .card-cover {
    height: 200px;
  }
}

@media (min-width: 1280px) {
  .history-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }

  .card-cover {
    height: 220px;
  }
}

.empty-state {
  padding-top: 20vh;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.text-danger {
  color: $danger;
}
</style>
