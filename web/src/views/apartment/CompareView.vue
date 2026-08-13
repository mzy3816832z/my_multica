<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getApartmentCompare } from '@/api/apartment'
import type { ApartmentCompareItem } from '@/types'

const route = useRoute()
const router = useRouter()

const items = ref<ApartmentCompareItem[]>([])
const loading = ref(false)
const error = ref('')

const ids = computed<number[]>(() => {
  const raw = String(route.query.ids || '')
  return raw
    .split(',')
    .map(Number)
    .filter((n) => !isNaN(n) && n > 0)
})

function goBack() {
  router.back()
}

function goDetail(id: number) {
  router.push('/apartments/' + id)
}

// ================= 字段展示与差异判断 =================

function formatPrice(item: ApartmentCompareItem): string {
  return item.min_monthly_rent != null ? `¥${item.min_monthly_rent}/月` : '暂无报价'
}

function formatArea(item: ApartmentCompareItem): string {
  return item.min_area != null ? `${item.min_area}㎡` : '暂无'
}

function formatOrientation(item: ApartmentCompareItem): string {
  return item.orientations.length > 0 ? item.orientations.join('、') : '暂无'
}

function formatPropertyFee(item: ApartmentCompareItem): string {
  const v = item.fees.property_fee
  if (v == null) return '暂无'
  return v === 0 ? '免物业费' : `¥${v}/月`
}

function formatWaterElectric(item: ApartmentCompareItem): string {
  const w = item.fees.water_fee_label
  const e = item.fees.electric_fee_label
  if (!w && !e) return '暂无'
  if (w && e) return w === e ? w : `${w}/${e}`
  return w || e || '暂无'
}

function formatServiceFee(item: ApartmentCompareItem): string {
  const v = item.fees.service_fee
  if (v == null) return '暂无'
  return v === 0 ? '无' : `¥${v}/月`
}

function formatOtherFees(item: ApartmentCompareItem): string {
  return item.fees.other_fees ? item.fees.other_fees : '暂无'
}

function formatFacilities(item: ApartmentCompareItem): string {
  return item.facilities.length > 0 ? item.facilities.join('、') : '暂无'
}

interface CompareField {
  key: string
  label: string
  format: (item: ApartmentCompareItem) => string
  raw: (item: ApartmentCompareItem) => string
}

const fields: CompareField[] = [
  { key: 'price', label: '价格', format: formatPrice, raw: (i) => (i.min_monthly_rent != null ? String(i.min_monthly_rent) : '') },
  { key: 'area', label: '面积', format: formatArea, raw: (i) => (i.min_area != null ? String(i.min_area) : '') },
  { key: 'orientation', label: '朝向', format: formatOrientation, raw: (i) => [...i.orientations].sort().join(',') },
  { key: 'property_fee', label: '物业费', format: formatPropertyFee, raw: (i) => (i.fees.property_fee != null ? String(i.fees.property_fee) : '') },
  { key: 'water_electric', label: '水电', format: formatWaterElectric, raw: (i) => [i.fees.water_fee_label, i.fees.electric_fee_label].filter(Boolean).sort().join('/') },
  { key: 'service_fee', label: '服务费', format: formatServiceFee, raw: (i) => (i.fees.service_fee != null ? String(i.fees.service_fee) : '') },
  { key: 'other_fees', label: '其他费用', format: formatOtherFees, raw: (i) => i.fees.other_fees || '' },
  { key: 'facilities', label: '设施', format: formatFacilities, raw: (i) => [...i.facilities].sort().join(',') },
]

const diffKeys = computed<Set<string>>(() => {
  const set = new Set<string>()
  if (items.value.length < 2) return set
  for (const field of fields) {
    const distinct = new Set(items.value.map((i) => field.raw(i)))
    if (distinct.size > 1) set.add(field.key)
  }
  return set
})

const gridColumns = computed(() => {
  const count = Math.max(items.value.length, 1)
  return `96px repeat(${count}, minmax(120px, 1fr))`
})

async function fetchCompare() {
  if (ids.value.length < 2) {
    error.value = '对比房源数量不足，请返回重新选择'
    return
  }
  loading.value = true
  error.value = ''
  try {
    items.value = await getApartmentCompare(ids.value)
    if (items.value.length < 2) {
      error.value = '可对比的房源不足，请返回重新选择'
    }
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(fetchCompare)
</script>

<template>
  <div class="compare-page">
    <van-nav-bar
      title="房源对比"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    />

    <div v-if="loading" class="flex justify-center py-20">
      <van-loading size="24">加载中...</van-loading>
    </div>

    <div v-else-if="error" class="empty-state">
      <van-empty image="search" :description="error">
        <van-button round type="primary" class="mt-4" @click="goBack">返回列表</van-button>
      </van-empty>
    </div>

    <div v-else class="compare-content">
      <div class="compare-table" :style="{ gridTemplateColumns: gridColumns }">
        <!-- 表头：封面 + 名称 -->
        <div class="cell header-label"></div>
        <div v-for="item in items" :key="item.id" class="cell header-cell">
          <div class="cover-box" @click="goDetail(item.id)">
            <van-image
              v-if="item.cover_image"
              :src="item.cover_image"
              fit="cover"
              class="w-full h-full"
              :alt="item.name"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-300">
              <van-icon name="photo-o" class="text-2xl" />
            </div>
          </div>
          <div class="name text-sm font-bold text-gray-900 line-clamp-2 mt-2">{{ item.name }}</div>
        </div>

        <!-- 字段行 -->
        <template v-for="field in fields" :key="field.key">
          <div class="cell field-label" :class="{ 'diff-label': diffKeys.has(field.key) }">
            {{ field.label }}
            <span v-if="diffKeys.has(field.key)" class="diff-tag">差异</span>
          </div>
          <div
            v-for="item in items"
            :key="item.id + '-' + field.key"
            class="cell field-value"
            :class="{ 'diff-highlight': diffKeys.has(field.key) }"
          >
            {{ field.format(item) }}
          </div>
        </template>
      </div>

      <div class="hint">长按高亮行表示该字段存在差异</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.compare-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.compare-content {
  padding: 12px;
}

.compare-table {
  display: grid;
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
  overflow-x: auto;
  min-width: 100%;
}

.cell {
  padding: 10px 8px;
  font-size: 13px;
  border-bottom: 1px solid #f2f3f5;
  border-right: 1px solid #f2f3f5;
  display: flex;
  align-items: center;
}

.header-label,
.field-label {
  background-color: #f7f8fa;
  color: #646566;
  font-weight: 600;
  position: sticky;
  left: 0;
  z-index: 1;
  justify-content: center;
}

.header-label {
  border-bottom: none;
}

.header-cell {
  flex-direction: column;
  align-items: flex-start;
}

.cover-box {
  width: 100%;
  height: 88px;
  background-color: #f7f8fa;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.field-label {
  flex-direction: column;
  gap: 4px;
}

.field-value {
  color: #323233;
  word-break: break-word;
  align-items: flex-start;
}

.diff-label {
  color: #ed6a0c;
}

.diff-tag {
  font-size: 10px;
  background-color: #fff7e8;
  color: #ed6a0c;
  border-radius: 4px;
  padding: 1px 4px;
  font-weight: 400;
}

.diff-highlight {
  background-color: #fff7e8;
  color: #ed6a0c;
  font-weight: 600;
}

.hint {
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  color: #969799;
}

.empty-state {
  padding-top: 20vh;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
