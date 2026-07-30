<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { getApartmentDetail, getRoomTypesByApartment } from '@/api/apartment'
import { addFavorite, removeFavorite } from '@/api/favorite'
import type { Apartment, RoomType } from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const apartmentId = ref(Number(route.params.id))
const apartment = ref<Apartment | null>(null)
const roomTypes = ref<RoomType[]>([])
const loading = ref(false)

async function fetchDetail() {
  if (!apartmentId.value || isNaN(apartmentId.value)) {
    showToast('房源ID无效')
    router.back()
    return
  }
  loading.value = true
  uiStore.showLoading('加载中...')
  try {
    const [aptRes, roomsRes] = await Promise.all([
      getApartmentDetail(apartmentId.value),
      getRoomTypesByApartment(apartmentId.value),
    ])
    apartment.value = aptRes
    roomTypes.value = roomsRes || []
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
    uiStore.hideLoading()
  }
}

async function toggleFavorite() {
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  if (!apartment.value) return
  const originalState = apartment.value.is_favorite
  try {
    if (originalState) {
      await removeFavorite(apartment.value.id)
      apartment.value.is_favorite = false
      showToast('已取消收藏')
    } else {
      await addFavorite(apartment.value.id)
      apartment.value.is_favorite = true
      showToast('收藏成功')
    }
  } catch {
    apartment.value.is_favorite = originalState
    showToast('操作失败，请重试')
  }
}

function goRoomTypeDetail(roomTypeId: number) {
  router.push('/room-types/' + roomTypeId)
}

function goBack() {
  router.back()
}

watch(() => route.params.id, (newId) => {
  const id = Number(newId)
  if (id && !isNaN(id) && id !== apartmentId.value) {
    apartmentId.value = id
    fetchDetail()
  }
})

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="apartment-detail">
    <!-- 顶部导航栏 -->
    <van-nav-bar
      :title="apartment?.name || '房源详情'"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    >
      <template #right>
        <van-icon
          v-if="authStore.isTenant"
          :name="apartment?.is_favorite ? 'star' : 'star-o'"
          :class="apartment?.is_favorite ? 'text-warning' : 'text-gray-400'"
          class="text-xl"
          @click="toggleFavorite"
        />
      </template>
    </van-nav-bar>

    <!-- 封面图 -->
    <div class="relative h-52 bg-gray-100">
      <van-image
        v-if="apartment?.cover_image"
        :src="apartment.cover_image"
        fit="cover"
        class="w-full h-full"
        :alt="apartment.name"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-gray-400">
        <van-icon name="photo-o" class="text-3xl" />
      </div>
    </div>

    <!-- 公寓信息 -->
    <div class="bg-white p-4">
      <h1 class="text-lg font-bold text-gray-900">{{ apartment?.name }}</h1>
      <div class="flex items-center mt-2 text-sm text-gray-500">
        <van-icon name="location-o" class="mr-1" />
        <span>
          {{ apartment?.district_name || '' }} {{ apartment?.street_name || '' }} {{ apartment?.detail_address || '' }}
        </span>
      </div>
      <div class="flex items-center mt-1 text-sm text-gray-500">
        <van-icon name="phone-o" class="mr-1" />
        <span>{{ apartment?.contact_phone || '暂无电话' }}</span>
      </div>
      <div class="mt-3 text-sm text-gray-600 leading-relaxed">
        {{ apartment?.description || '暂无描述' }}
      </div>
      <div class="mt-3 flex items-baseline">
        <span class="text-danger text-xl font-bold">¥{{ apartment?.min_monthly_rent || '?' }}</span>
        <span class="text-sm text-gray-500 ml-1">/月起</span>
      </div>
    </div>

    <!-- 房型列表 -->
    <div class="mt-3 bg-white p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-base font-bold text-gray-900">可选户型</h2>
        <span class="text-sm text-gray-400">{{ roomTypes.length }} 种户型</span>
      </div>

      <div v-if="roomTypes.length === 0 && !loading" class="py-8">
        <van-empty description="暂无户型信息" />
      </div>

      <div class="space-y-3">
        <div
          v-for="room in roomTypes"
          :key="room.id"
          class="flex gap-3 p-3 bg-gray-50 rounded-xl"
          @click="goRoomTypeDetail(room.id)"
        >
          <!-- 首图 -->
          <div class="w-24 h-24 flex-shrink-0 bg-gray-200 rounded-lg overflow-hidden">
            <van-image
              v-if="room.images && room.images.length > 0"
              :src="room.images[0]"
              fit="cover"
              class="w-full h-full"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-400">
              <van-icon name="photo-o" class="text-xl" />
            </div>
          </div>
          <!-- 信息 -->
          <div class="flex-1 min-w-0">
            <div class="text-base font-bold text-gray-900 line-clamp-1">{{ room.name }}</div>
            <div class="mt-1 flex flex-wrap gap-1">
              <van-tag type="primary">{{ room.layout_type_label || room.layout_type }}</van-tag>
              <van-tag type="success">{{ room.window_type_label || room.window_type }}</van-tag>
              <van-tag>{{ room.floor }}层</van-tag>
            </div>
            <div class="mt-2 flex items-baseline">
              <span class="text-danger text-base font-bold">¥{{ room.min_monthly_rent || '?' }}</span>
              <span class="text-xs text-gray-500 ml-1">/月起</span>
            </div>
          </div>
          <div class="flex items-center text-gray-400">
            <van-icon name="arrow" />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部占位（安全区） -->
    <div class="h-6" />
  </div>
</template>

<style scoped lang="scss">
.apartment-detail {
  min-height: 100vh;
  background-color: $bg-color;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.text-warning {
  color: $warning;
}

.text-danger {
  color: $danger;
}
</style>
