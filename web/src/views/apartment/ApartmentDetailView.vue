<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { getApartmentDetail } from '@/api/apartment'
import { addFavorite, removeFavorite } from '@/api/favorite'
import type { Apartment } from '@/types'
import FeeDetailCard from '@/components/business/FeeDetailCard.vue'
import FacilityGroup from '@/components/business/FacilityGroup.vue'
import PhoneActionSheet from '@/components/business/PhoneActionSheet.vue'
import ShareSheet from '@/components/business/ShareSheet.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const apartmentId = ref(Number(route.params.id))
const apartment = ref<Apartment | null>(null)
const loading = ref(false)
const isOffline = ref(false)
const phoneSheetVisible = ref(false)
const shareSheetVisible = ref(false)

const allFacilities = computed<string[]>(() => {
  if (!apartment.value?.room_types) return []
  const set = new Set<string>()
  for (const room of apartment.value.room_types) {
    for (const f of room.facilities) {
      set.add(f)
    }
  }
  return Array.from(set)
})

async function fetchDetail() {
  if (!apartmentId.value || isNaN(apartmentId.value)) {
    showToast('房源ID无效')
    router.back()
    return
  }
  loading.value = true
  uiStore.showLoading('加载中...')
  isOffline.value = false
  try {
    const aptRes = await getApartmentDetail(apartmentId.value)
    apartment.value = aptRes
  } catch (err: any) {
    if (err?.code === 410001) {
      isOffline.value = true
    }
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

function goFavorites() {
  router.push('/profile/favorites')
}

function showPhoneSheet() {
  phoneSheetVisible.value = true
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
    <van-nav-bar
      :title="apartment?.name || '房源详情'"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    >
      <template #right>
        <div class="flex items-center gap-3">
          <van-icon
            v-if="!isOffline"
            name="share-o"
            class="text-xl text-gray-600 cursor-pointer"
            @click="shareSheetVisible = true"
          />
          <van-icon
            v-if="authStore.isTenant && !isOffline"
            :name="apartment?.is_favorite ? 'star' : 'star-o'"
            :class="apartment?.is_favorite ? 'text-warning' : 'text-gray-400'"
            class="text-xl"
            @click="toggleFavorite"
          />
        </div>
      </template>
    </van-nav-bar>

    <div v-if="isOffline" class="offline-placeholder">
      <van-empty image="error" description="该房源已下架">
        <template #description>
          <div class="text-center">
            <p class="text-gray-500 mt-2">该房源已下架或已被删除</p>
            <p class="text-gray-400 text-sm mt-1">您可以在收藏列表中取消收藏</p>
          </div>
        </template>
        <van-button
          round
          type="primary"
          class="mt-6"
          @click="goFavorites"
        >
          去收藏列表
        </van-button>
      </van-empty>
    </div>

    <template v-else>
      <div class="detail-layout">
        <div class="detail-cover">
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

        <div class="detail-info">
          <div class="bg-white p-4">
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold text-gray-900">{{ apartment?.name }}</h1>
              <van-tag v-if="apartment?.verified" type="success" size="medium">平台核验</van-tag>
            </div>
            <div class="flex items-center mt-2 text-sm text-gray-500">
              <van-icon name="location-o" class="mr-1" />
              <span>
                {{ apartment?.district_name || '' }} {{ apartment?.street_name || '' }} {{ apartment?.detail_address || '' }}
              </span>
            </div>
            <div class="flex items-center mt-1 text-sm" :class="apartment?.contact_phone ? 'text-primary cursor-pointer' : 'text-gray-500'" @click="apartment?.contact_phone ? showPhoneSheet() : undefined">
              <van-icon name="phone-o" class="mr-1" />
              <span>{{ apartment?.contact_phone || '暂无电话' }}</span>
            </div>
            <div class="mt-3 text-sm text-gray-600 leading-relaxed">
              {{ apartment?.description || '暂无描述' }}
            </div>
            <div class="mt-3 flex items-baseline">
              <span v-if="apartment?.min_monthly_rent != null" class="text-danger text-xl font-bold">¥{{ apartment.min_monthly_rent }}</span>
              <span v-else class="text-sm text-gray-400">暂无报价</span>
              <span v-if="apartment?.min_monthly_rent != null" class="text-sm text-gray-500 ml-1">/月起</span>
            </div>
          </div>

          <div v-if="apartment?.landlord_info" class="mt-3 bg-white p-4">
            <h2 class="text-base font-bold text-gray-900 mb-2">商家信息</h2>
            <div class="flex items-center gap-4 text-sm text-gray-600">
              <div class="flex items-center gap-1">
                <van-icon name="phone-o" />
                <span>{{ apartment.landlord_info.verified_phone ? '已验证手机号' : '手机号未验证' }}</span>
                <van-tag v-if="apartment.landlord_info.verified_phone" type="success" class="ml-1 text-xs">已认证</van-tag>
              </div>
              <div class="flex items-center gap-1">
                <van-icon name="home-o" />
                <span>在架房源 {{ apartment.landlord_info.active_listing_count }} 套</span>
              </div>
            </div>
          </div>

          <div class="mt-3 bg-white p-4">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-base font-bold text-gray-900">可选户型</h2>
              <span class="text-sm text-gray-400">{{ apartment?.room_types?.length || 0 }} 种户型</span>
            </div>

            <div v-if="!apartment?.room_types || apartment.room_types.length === 0" class="py-8">
              <van-empty description="暂无户型信息" />
            </div>

            <div class="space-y-3">
              <div
                v-for="room in apartment?.room_types || []"
                :key="room.id"
                class="flex gap-3 p-3 bg-gray-50 rounded-xl"
                @click="goRoomTypeDetail(room.id)"
              >
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
                <div class="flex-1 min-w-0">
                  <div class="text-base font-bold text-gray-900 line-clamp-1">{{ room.name }}</div>
                  <div class="mt-1 flex flex-wrap gap-1">
                    <van-tag type="primary">{{ room.layout_type_label || room.layout_type }}</van-tag>
                    <van-tag type="success">{{ room.window_type_label || room.window_type }}</van-tag>
                    <van-tag>{{ room.floor }}层</van-tag>
                  </div>
                  <div class="mt-2 flex items-baseline">
                    <span v-if="room.min_monthly_rent !== null && room.min_monthly_rent !== undefined" class="text-danger text-base font-bold">¥{{ room.min_monthly_rent }}</span>
                    <span v-else class="text-sm text-gray-400">暂无报价</span>
                    <span v-if="room.min_monthly_rent !== null && room.min_monthly_rent !== undefined" class="text-xs text-gray-500 ml-1">/月起</span>
                  </div>
                </div>
                <div class="flex items-center text-gray-400">
                  <van-icon name="arrow" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <FeeDetailCard :apartment="apartment" />

      <FacilityGroup :facilities="allFacilities" />

      <div class="h-6" />

      <PhoneActionSheet
        v-model:visible="phoneSheetVisible"
        :phone="apartment?.contact_phone || ''"
      />

      <ShareSheet
        v-model:visible="shareSheetVisible"
        :apartment-id="apartment?.id || 0"
        :apartment-name="apartment?.name || ''"
        :cover-image="apartment?.cover_image || ''"
        :price="apartment?.min_monthly_rent"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
.apartment-detail {
  min-height: 100vh;
  background-color: $bg-color;
}

.detail-layout {
  display: flex;
  flex-direction: column;
}

.detail-cover {
  width: 100%;
  height: 208px;
  background-color: #f7f8fa;
}

.detail-info {
  width: 100%;
}

@media (min-width: 768px) {
  .detail-layout {
    flex-direction: row;
    gap: 24px;
    max-width: 1200px;
    margin: 24px auto;
    padding: 0 24px;
    align-items: flex-start;
  }

  .detail-cover {
    width: 45%;
    height: 360px;
    border-radius: 12px;
    overflow: hidden;
    flex-shrink: 0;
  }

  .detail-info {
    flex: 1;
    min-width: 0;
  }

  .detail-info .bg-white {
    border-radius: 12px;
  }

  .detail-info .mt-3.bg-white {
    margin-top: 16px !important;
  }
}

.offline-placeholder {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 80px;
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
