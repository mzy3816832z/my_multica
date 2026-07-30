<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { getRoomTypeDetail } from '@/api/apartment'
import { getDicts } from '@/api/dict'
import type { RoomType, RentalPlan, DictItem } from '@/types'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()

const roomTypeId = ref(Number(route.params.id))
const roomType = ref<RoomType | null>(null)
const loading = ref(false)

// 字典映射（用于设施标签翻译）
const facilityDicts = ref<DictItem[]>([])
const paymentDicts = ref<DictItem[]>([])
const leaseDicts = ref<DictItem[]>([])

async function loadDicts() {
  try {
    const [facilities, payments, leases] = await Promise.all([
      getDicts('facility'),
      getDicts('payment_method'),
      getDicts('lease_term'),
    ])
    facilityDicts.value = facilities
    paymentDicts.value = payments
    leaseDicts.value = leases
  } catch {
    // 静默失败，使用原始编码展示
  }
}

function getFacilityLabel(code: string) {
  const found = facilityDicts.value.find((d) => d.code === code)
  return found ? found.label : code
}

function getPaymentLabel(code: string) {
  const found = paymentDicts.value.find((d) => d.code === code)
  return found ? found.label : code
}

function getLeaseLabel(code: string) {
  const found = leaseDicts.value.find((d) => d.code === code)
  return found ? found.label : code
}

async function fetchDetail() {
  if (!roomTypeId.value || isNaN(roomTypeId.value)) {
    showToast('户型ID无效')
    router.back()
    return
  }
  loading.value = true
  uiStore.showLoading('加载中...')
  try {
    const res = await getRoomTypeDetail(roomTypeId.value)
    roomType.value = res
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
    uiStore.hideLoading()
  }
}

function goBack() {
  router.back()
}

// 轮播图当前索引
const currentImageIndex = ref(0)

function onImageChange(index: number) {
  currentImageIndex.value = index
}

watch(() => route.params.id, (newId) => {
  const id = Number(newId)
  if (id && !isNaN(id) && id !== roomTypeId.value) {
    roomTypeId.value = id
    fetchDetail()
  }
})

onMounted(() => {
  loadDicts()
  fetchDetail()
})
</script>

<template>
  <div class="room-type-detail">
    <!-- 顶部导航栏 -->
    <van-nav-bar
      :title="roomType?.name || '户型详情'"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    />

    <!-- 图片轮播 -->
    <div class="relative bg-gray-100">
      <van-swipe
        v-if="roomType?.images && roomType.images.length > 0"
        class="h-56"
        :autoplay="3000"
        @change="onImageChange"
      >
        <van-swipe-item v-for="(img, idx) in roomType.images" :key="idx">
          <van-image
            :src="img"
            fit="cover"
            class="w-full h-full"
          />
        </van-swipe-item>
      </van-swipe>
      <div v-else class="h-56 flex items-center justify-center text-gray-400">
        <van-icon name="photo-o" class="text-3xl" />
      </div>
      <!-- 图片计数器 -->
      <div
        v-if="roomType?.images && roomType.images.length > 0"
        class="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-2 py-1 rounded-full"
      >
        {{ currentImageIndex + 1 }} / {{ roomType.images.length }}
      </div>
    </div>

    <!-- 户型基本信息 -->
    <div class="bg-white p-4">
      <h1 class="text-lg font-bold text-gray-900">{{ roomType?.name }}</h1>
      <div class="mt-2 flex flex-wrap gap-2">
        <van-tag type="primary" size="medium">{{ roomType?.layout_type_label || roomType?.layout_type }}</van-tag>
        <van-tag type="success" size="medium">{{ roomType?.window_type_label || roomType?.window_type }}</van-tag>
        <van-tag size="medium">{{ roomType?.floor }}层</van-tag>
      </div>
    </div>

    <!-- 设施标签 -->
    <div class="mt-3 bg-white p-4">
      <h2 class="text-base font-bold text-gray-900 mb-3">房屋设施</h2>
      <div v-if="roomType?.facilities && roomType.facilities.length > 0" class="flex flex-wrap gap-2">
        <van-tag
          v-for="f in roomType.facilities"
          :key="f"
          type="primary"
          plain
          size="medium"
          round
        >
          <template #default>
            <span class="flex items-center gap-1">
              <van-icon name="passed" class="text-xs" />
              {{ getFacilityLabel(f) }}
            </span>
          </template>
        </van-tag>
      </div>
      <div v-else class="text-sm text-gray-400">暂无设施信息</div>
    </div>

    <!-- 租期租金方案 -->
    <div class="mt-3 bg-white p-4">
      <h2 class="text-base font-bold text-gray-900 mb-3">租期租金方案</h2>
      <div v-if="roomType?.rental_plans && roomType.rental_plans.length > 0" class="space-y-3">
        <div
          v-for="plan in roomType.rental_plans"
          :key="plan.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-xl"
        >
          <div>
            <div class="text-sm text-gray-900 font-medium">
              {{ getLeaseLabel(plan.lease_term) }}
            </div>
            <div class="text-xs text-gray-500 mt-1">
              {{ getPaymentLabel(plan.payment_method) }}
            </div>
          </div>
          <div class="text-right">
            <div class="text-danger text-lg font-bold">
              ¥{{ plan.monthly_rent }}
            </div>
            <div class="text-xs text-gray-500">/月</div>
          </div>
        </div>
      </div>
      <div v-else class="text-sm text-gray-400">暂无租金方案</div>
    </div>

    <!-- 底部占位（安全区） -->
    <div class="h-6" />
  </div>
</template>

<style scoped lang="scss">
.room-type-detail {
  min-height: 100vh;
  background-color: $bg-color;
}

.text-danger {
  color: $danger;
}
</style>
