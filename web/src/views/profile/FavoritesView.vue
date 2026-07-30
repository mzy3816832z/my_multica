<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { getFavorites, removeFavorite } from '@/api/favorite'
import type { Apartment } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const list = ref<Apartment[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)

async function fetchList(isRefresh = false) {
  if (loading.value) return
  loading.value = true
  try {
    const currentPage = isRefresh ? 1 : page.value
    const data = await getFavorites({ page: currentPage, page_size: pageSize.value })
    if (isRefresh) {
      list.value = data.items
      page.value = 1
    } else {
      list.value.push(...data.items)
    }
    total.value = data.total
    finished.value = list.value.length >= data.total
    if (!isRefresh) {
      page.value++
    }
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function onLoad() {
  fetchList()
}

function onRefresh() {
  finished.value = false
  fetchList(true)
}

function goDetail(id: number) {
  router.push('/apartments/' + id)
}

async function handleCancel(id: number, event: Event) {
  event.stopPropagation()
  try {
    await removeFavorite(id)
    showToast('已取消收藏')
    list.value = list.value.filter((item) => item.id !== id)
    total.value = Math.max(0, total.value - 1)
  } catch {
    // 错误已在 request 拦截器中 toast
  }
}

onMounted(() => {
  fetchList(true)
})
</script>

<template>
  <div class="favorites-page">
    <!-- 顶部导航栏 -->
    <van-nav-bar title="我的收藏" left-arrow fixed placeholder @click-left="router.back" />

    <!-- 列表内容 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="list.length === 0 && !loading" class="empty-state">
          <van-empty description="暂无收藏" />
        </div>

        <div class="px-3 py-2 space-y-3">
          <div
            v-for="item in list"
            :key="item.id"
            class="bg-white rounded-xl overflow-hidden shadow-sm relative"
            @click="goDetail(item.id)"
          >
            <!-- 封面图 -->
            <div class="relative h-44 bg-gray-100">
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
            <!-- 信息区 -->
            <div class="p-3">
              <h3 class="text-base font-bold text-gray-900 line-clamp-1">{{ item.name }}</h3>
              <p class="text-sm text-gray-500 mt-1 flex items-center">
                <van-icon name="location-o" class="mr-1" />
                {{ item.district_name || '' }} {{ item.street_name || '' }}
              </p>
            </div>
            <!-- 取消收藏按钮 -->
            <div class="absolute top-2 right-2">
              <van-button
                size="mini"
                type="danger"
                plain
                round
                icon="delete-o"
                @click="handleCancel(item.id, $event)"
              >
                取消收藏
              </van-button>
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<style scoped lang="scss">
.favorites-page {
  min-height: 100vh;
  background-color: $bg-color;
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
</style>
