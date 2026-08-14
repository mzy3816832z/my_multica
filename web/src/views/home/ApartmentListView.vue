<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getApartments, getMetroLines } from '@/api/apartment'
import { getDistricts } from '@/api/dict'
import { addFavorite, removeFavorite } from '@/api/favorite'
import type { Apartment, District, DictItem, MetroLine, MetroStation } from '@/types'
import MapView from './MapView.vue'

const router = useRouter()
const authStore = useAuthStore()

const viewMode = ref<'list' | 'map'>('list')

// ================= 列表数据 =================
const list = ref<Apartment[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)

// ================= 搜索 =================
const keyword = ref('')
const showSearch = ref(false)

// 搜索历史（localStorage，最多10条）
const SEARCH_HISTORY_KEY = 'apt_search_history'
const MAX_HISTORY = 10

interface SearchHistoryItem {
  keyword: string
  timestamp: number
}

function loadSearchHistory(): SearchHistoryItem[] {
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw) as SearchHistoryItem[]
  } catch {
    return []
  }
}

const searchHistory = ref<SearchHistoryItem[]>(loadSearchHistory())

function saveSearchHistory(kw: string) {
  if (!kw.trim()) return
  const history = searchHistory.value.filter(h => h.keyword !== kw.trim())
  history.unshift({ keyword: kw.trim(), timestamp: Date.now() })
  if (history.length > MAX_HISTORY) history.splice(MAX_HISTORY)
  searchHistory.value = history
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history))
}

function removeSearchHistory(index: number) {
  searchHistory.value.splice(index, 1)
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(searchHistory.value))
}

function clearSearchHistory() {
  searchHistory.value = []
  localStorage.removeItem(SEARCH_HISTORY_KEY)
}

function onHistoryClick(kw: string) {
  keyword.value = kw
  onSearch()
}

// ================= 筛选 =================
const showFilter = ref(false)

const filter = reactive({
  district_id: undefined as number | undefined,
  street_ids: [] as number[],
  layout_types: [] as string[],
  lease_terms: [] as string[],
  min_price: undefined as number | undefined,
  max_price: undefined as number | undefined,
  metro_station_ids: [] as number[],
})

const sort = ref('latest')
const sortOptions = [
  { text: '最新上架', value: 'latest' },
  { text: '价格从低到高', value: 'price_asc' },
  { text: '价格从高到低', value: 'price_desc' },
]


const districts = ref<District[]>([])

async function loadDistricts() {
  try {
    const res = await getDistricts({ level: 1 })
    const sorted = res.sort((a: District, b: District) => {
      return (a.sort || 0) - (b.sort || 0)
    })
    districts.value = sorted
  } catch {
    districts.value = []
  }
}

const streets = ref<District[]>([])

// 户型静态映射
const layoutTypes = ref<DictItem[]>([
  { code: 'studio', label: '一室', sort: 1 },
  { code: 'one_bedroom', label: '一室一厅', sort: 2 },
  { code: 'two_bedroom', label: '两室一厅', sort: 3 },
  { code: 'two_bedroom_2', label: '两室两厅', sort: 4 },
  { code: 'three_bedroom', label: '三室一厅', sort: 5 },
  { code: 'three_bedroom_2', label: '三室两厅', sort: 6 },
  { code: 'loft', label: 'LOFT', sort: 7 },
  { code: 'duplex', label: '复式', sort: 8 },
])

// 租期静态映射
const leaseTerms = ref<DictItem[]>([
  { code: '1_month', label: '1个月', sort: 1 },
  { code: '3_months', label: '3个月', sort: 2 },
  { code: '6_months', label: '半年', sort: 3 },
  { code: '1_year', label: '1年', sort: 4 },
  { code: '18_months', label: '18个月', sort: 5 },
  { code: '2_years', label: '2年', sort: 6 },
])

const streetsLoading = ref(false)
const streetsError = ref('')

const activeFilterCount = computed(() => {
  let count = 0
  if (filter.district_id !== undefined) count++
  if (filter.street_ids.length > 0) count++
  if (filter.layout_types.length > 0) count++
  if (filter.lease_terms.length > 0) count++
  if (filter.min_price !== undefined || filter.max_price !== undefined) count++
  if (filter.metro_station_ids.length > 0) count++
  return count
})

// ================= 地铁筛选 =================
const metroLines = ref<MetroLine[]>([])
const metroStations = ref<MetroStation[]>([])

async function loadMetroLines() {
  try {
    const lines = await getMetroLines()
    metroLines.value = lines
  } catch {
    metroLines.value = []
  }
}

function selectMetroLine(line: MetroLine) {
  if (selectedMetroLineId.value === line.id) {
    selectedMetroLineId.value = null
    metroStations.value = []
    filter.metro_station_ids = []
  } else {
    selectedMetroLineId.value = line.id
    metroStations.value = line.stations
    filter.metro_station_ids = []
  }
}

const selectedMetroLineId = ref<number | null>(null)

function toggleMetroStation(id: number) {
  const idx = filter.metro_station_ids.indexOf(id)
  if (idx > -1) filter.metro_station_ids.splice(idx, 1)
  else filter.metro_station_ids.push(id)
}

// ================= 加载街道数据（保留接口调用） =================
async function loadStreets(parentId: number) {
  streetsLoading.value = true
  streetsError.value = ''
  try {
    const res = await getDistricts({ level: 2, parent_id: parentId })
    streets.value = res
  } catch {
    streetsError.value = '加载街道失败'
  } finally {
    streetsLoading.value = false
  }
}

watch(() => filter.district_id, (val) => {
  filter.street_ids = []
  streets.value = []
  if (val) {
    loadStreets(val)
  }
})

// ================= 加载列表 =================
async function fetchList(isRefresh = false) {
  if (loading.value) return
  loading.value = true
  try {
    const currentPage = isRefresh ? 1 : page.value
    const params = {
      keyword: keyword.value || undefined,
      district_id: filter.district_id,
      street_ids: filter.street_ids.length > 0 ? filter.street_ids : undefined,
      layout_types: filter.layout_types.length > 0 ? filter.layout_types : undefined,
      lease_terms: filter.lease_terms.length > 0 ? filter.lease_terms : undefined,
      min_price: filter.min_price,
      max_price: filter.max_price,
      metro_station_ids: filter.metro_station_ids.length > 0 ? filter.metro_station_ids : undefined,
      sort: sort.value !== 'latest' ? sort.value : undefined,
      page: currentPage,
      page_size: pageSize.value,
    }
    const data = await getApartments(params)
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
    if (sort.value !== 'latest') {
      showToast('排序加载失败，请重试')
    }
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

function onSearch() {
  saveSearchHistory(keyword.value)
  showSearch.value = false
  onRefresh()
}

function onFilterConfirm() {
  showFilter.value = false
  onRefresh()
}

function onFilterReset() {
  filter.district_id = undefined
  filter.street_ids = []
  filter.layout_types = []
  filter.lease_terms = []
  filter.min_price = undefined
  filter.max_price = undefined
  filter.metro_station_ids = []
  streets.value = []
  selectedMetroLineId.value = null
  metroStations.value = []
}

function onFilterClear() {
  onFilterReset()
  onFilterConfirm()
}

function onSortChange() {
  scrollToTop()
  onRefresh()
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goDetail(id: number) {
  router.push('/apartments/' + id)
}

function goCreate() {
  router.push('/profile/apartments/create')
}

function toggleStreet(id: number) {
  const idx = filter.street_ids.indexOf(id)
  if (idx > -1) filter.street_ids.splice(idx, 1)
  else filter.street_ids.push(id)
}

function toggleLayoutType(code: string) {
  const idx = filter.layout_types.indexOf(code)
  if (idx > -1) filter.layout_types.splice(idx, 1)
  else filter.layout_types.push(code)
}

function toggleLeaseTerm(code: string) {
  const idx = filter.lease_terms.indexOf(code)
  if (idx > -1) filter.lease_terms.splice(idx, 1)
  else filter.lease_terms.push(code)
}

async function toggleFavorite(apartment: Apartment, event: Event) {
  event.stopPropagation()
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    router.push({ path: '/login', query: { redirect: '/apartments' } })
    return
  }
  const originalState = apartment.is_favorite
  try {
    if (originalState) {
      await removeFavorite(apartment.id)
      apartment.is_favorite = false
      showToast('已取消收藏')
    } else {
      await addFavorite(apartment.id)
      apartment.is_favorite = true
      showToast('收藏成功')
    }
  } catch {
    apartment.is_favorite = originalState
    showToast('操作失败，请重试')
  }
}

// ================= 对比选择模式 =================
const selectMode = ref(false)
const selectedIds = ref<number[]>([])
const MAX_COMPARE = 3

let longPressTimer: number | null = null
let suppressClick = false

function clearLongPress() {
  if (longPressTimer !== null) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function onCardPress(id: number) {
  if (selectMode.value) return
  clearLongPress()
  longPressTimer = window.setTimeout(() => {
    suppressClick = true
    selectMode.value = true
    toggleSelect(id)
  }, 500)
}

function onCardRelease() {
  clearLongPress()
}

function onCardClick(id: number) {
  if (suppressClick) {
    suppressClick = false
    return
  }
  if (selectMode.value) {
    toggleSelect(id)
  } else {
    goDetail(id)
  }
}

function toggleSelect(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx > -1) {
    selectedIds.value.splice(idx, 1)
  } else {
    if (selectedIds.value.length >= MAX_COMPARE) {
      showToast('最多对比3套')
      return
    }
    selectedIds.value.push(id)
  }
}

function isSelected(id: number) {
  return selectedIds.value.includes(id)
}

function exitSelectMode() {
  selectMode.value = false
  selectedIds.value = []
  clearLongPress()
}

function startCompare() {
  if (selectedIds.value.length < 2) return
  const ids = selectedIds.value.join(',')
  exitSelectMode()
  router.push({ path: '/compare', query: { ids } })
}

// ================= 初始化 =================
onMounted(() => {
  loadDistricts()
  loadMetroLines()
  fetchList(true)
})
</script>

<template>
  <div class="apartment-list" :class="{ 'has-compare-bar': selectMode }">
    <!-- 顶部搜索栏 -->
    <div class="sticky top-0 z-10 bg-white shadow-sm">
      <div class="flex items-center px-3 py-2 gap-2">
        <div
          class="flex-1 flex items-center bg-gray-100 rounded-full px-3 py-2"
          @click="showSearch = true"
        >
          <van-icon name="search" class="text-gray-400 mr-2" />
          <span class="text-sm text-gray-400 flex-1">
            {{ keyword || '搜索房源名称' }}
          </span>
          <van-icon v-if="keyword" name="clear" class="text-gray-400" @click.stop="keyword = ''; onRefresh()" />
        </div>
        <div
          class="flex items-center text-sm text-gray-600 px-2 py-1"
          :class="{ 'text-primary font-medium': activeFilterCount > 0 }"
          @click="showFilter = true"
        >
          <van-icon name="filter-o" class="mr-1" />
          筛选
          <van-badge v-if="activeFilterCount > 0" :content="activeFilterCount" class="ml-1" />
        </div>
      </div>

      <van-dropdown-menu active-color="#1989fa">
        <van-dropdown-item
          v-model="sort"
          :options="sortOptions"
          @change="onSortChange"
        >
          <template #title>
            <span class="text-sm">{{ sortOptions.find(o => o.value === sort)?.text || '排序' }}</span>
          </template>
        </van-dropdown-item>
      </van-dropdown-menu>

      <div class="flex items-center border-t border-gray-100">
        <div
          class="flex-1 text-center py-2 text-sm font-medium cursor-pointer"
          :class="viewMode === 'list' ? 'text-primary border-b-2 border-primary' : 'text-gray-500'"
          @click="viewMode = 'list'"
        >
          <van-icon name="bars" class="mr-1" />列表
        </div>
        <div
          class="flex-1 text-center py-2 text-sm font-medium cursor-pointer"
          :class="viewMode === 'map' ? 'text-primary border-b-2 border-primary' : 'text-gray-500'"
          @click="viewMode = 'map'"
        >
          <van-icon name="location-o" class="mr-1" />地图
        </div>
      </div>
    </div>

    <div v-if="viewMode === 'map'" class="map-view-wrapper">
      <MapView :apartments="list" @go-detail="goDetail" />
    </div>

    <template v-else>
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="list.length === 0 && !loading" class="empty-state">
          <van-empty description="暂无房源" />
          <div v-if="keyword || activeFilterCount > 0" class="px-4 text-center">
            <p class="text-sm text-gray-400 mb-3">试试搜索行政区或街道名</p>
          </div>
        </div>

        <div class="apartment-grid px-3 py-2">
          <div
            v-for="item in list"
            :key="item.id"
            class="apartment-card bg-white rounded-xl overflow-hidden shadow-sm relative"
            :class="{ 'card-selected': selectMode && isSelected(item.id) }"
            @click="onCardClick(item.id)"
            @touchstart="onCardPress(item.id)"
            @touchend="onCardRelease"
            @touchmove="onCardRelease"
            @mousedown="onCardPress(item.id)"
            @mouseup="onCardRelease"
            @mouseleave="onCardRelease"
            @contextmenu.prevent
          >
            <!-- 选择模式勾选标识 -->
            <div
              v-if="selectMode"
              class="select-indicator"
              :class="{ active: isSelected(item.id) }"
            >
              <van-icon :name="isSelected(item.id) ? 'success' : 'circle'" />
            </div>
            <!-- 图片 -->
            <div class="card-image bg-gray-100">
              <van-image
                :src="item.cover_image"
                fit="cover"
                class="w-full h-full"
                :alt="item.name"
              />
            </div>
            <!-- 信息 -->
            <div class="card-info flex flex-col justify-between min-w-0">
              <div>
                <div class="flex items-center gap-1">
                  <h3 class="text-base font-bold text-gray-900 line-clamp-1">{{ item.name }}</h3>
                  <van-tag v-if="item.verified" type="success" size="medium" class="text-xs flex-shrink-0">平台核验</van-tag>
                </div>
                <p class="text-sm text-gray-500 mt-1 flex items-center">
                  <van-icon name="location-o" class="mr-1" />
                  {{ item.district_name || '' }} {{ item.street_name || '' }}
                </p>
              </div>
              <div class="flex items-center justify-between mt-2">
                <span v-if="item.min_monthly_rent != null" class="text-primary font-bold">¥{{ item.min_monthly_rent }}/月起</span>
                <span v-else class="text-sm text-gray-400">暂无报价</span>
                <van-icon
                  v-if="authStore.isTenant && !selectMode"
                  :name="item.is_favorite ? 'star' : 'star-o'"
                  :class="item.is_favorite ? 'text-warning' : 'text-gray-400'"
                  class="text-xl"
                  @click.stop="toggleFavorite(item, $event)"
                />
              </div>
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>
    </template>

    <!-- 商家悬浮发布按钮 -->
    <div
      v-if="authStore.isLandlord"
      class="fixed-fab"
      @click="goCreate"
    >
      <div class="w-12 h-12 bg-primary rounded-full flex items-center justify-center shadow-lg">
        <van-icon name="plus" class="text-white text-xl" />
      </div>
    </div>

    <!-- 对比选择底部栏 -->
    <div v-if="selectMode" class="compare-bar safe-area-bottom">
      <span class="compare-count">已选 {{ selectedIds.length }}/{{ MAX_COMPARE }} 套</span>
      <div class="flex gap-2">
        <van-button size="small" plain @click="exitSelectMode">取消</van-button>
        <van-button
          size="small"
          type="primary"
          :disabled="selectedIds.length < 2"
          @click="startCompare"
        >开始对比</van-button>
      </div>
    </div>

    <!-- 搜索弹窗 -->
    <van-popup v-model:show="showSearch" position="top" :style="{ height: '100%' }" class="bg-white">
      <div class="flex items-center px-3 py-2 border-b border-gray-100">
        <van-search
          v-model="keyword"
          placeholder="搜索房源名称、地址或描述"
          show-action
          maxlength="30"
          class="flex-1"
          @search="onSearch"
        >
          <template #action>
            <span class="text-primary text-sm" @click="onSearch">搜索</span>
          </template>
        </van-search>
        <span class="text-sm text-gray-500 ml-2" @click="showSearch = false">取消</span>
      </div>

      <!-- 搜索历史 -->
      <div v-if="searchHistory.length > 0" class="px-4 pt-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-bold text-gray-900">搜索历史</span>
          <van-icon name="delete-o" class="text-gray-400" @click="clearSearchHistory" />
        </div>
        <div class="flex flex-wrap gap-2">
          <div
            v-for="(item, index) in searchHistory"
            :key="item.timestamp"
            class="flex items-center bg-gray-100 rounded-full px-3 py-1"
          >
            <span class="text-sm text-gray-700" @click="onHistoryClick(item.keyword)">{{ item.keyword }}</span>
            <van-icon
              name="cross"
              class="text-gray-400 ml-1 text-xs"
              @click.stop="removeSearchHistory(index)"
            />
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 筛选抽屉 -->
    <van-popup v-model:show="showFilter" position="right" :style="{ width: '80%', height: '100%' }" class="bg-white">
      <div class="flex flex-col h-full">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <span class="text-base font-bold">筛选条件</span>
          <span v-if="activeFilterCount > 0" class="text-sm text-gray-400" @click="onFilterClear">清空</span>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
          <!-- 行政区 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">行政区</div>
            <div class="flex flex-wrap gap-2">
              <van-tag
                v-for="d in districts"
                :key="d.id"
                :type="filter.district_id === d.id ? 'primary' : 'default'"
                size="large"
                round
                @click="filter.district_id = filter.district_id === d.id ? undefined : d.id"
              >
                {{ d.name }}
              </van-tag>
            </div>
          </div>

          <!-- 街道 -->
          <div v-if="filter.district_id !== undefined || streets.length > 0">
            <div class="text-sm font-bold text-gray-900 mb-2">街道/镇</div>
            <van-loading v-if="streetsLoading" size="20" class="py-2" />
            <div v-else-if="streetsError" class="text-sm text-red-500 py-2">{{ streetsError }}</div>
            <div v-else-if="streets.length === 0" class="text-sm text-gray-400 py-2">暂无街道/镇数据</div>
            <div v-else class="flex flex-wrap gap-2">
              <van-tag
                v-for="s in streets"
                :key="s.id"
                :type="filter.street_ids.includes(s.id) ? 'primary' : 'default'"
                size="large"
                round
                @click="toggleStreet(s.id)"
              >
                {{ s.name }}
              </van-tag>
            </div>
          </div>

          <!-- 户型 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">户型</div>
            <div class="flex flex-wrap gap-2">
              <van-tag
                v-for="l in layoutTypes"
                :key="l.code"
                :type="filter.layout_types.includes(l.code) ? 'primary' : 'default'"
                size="large"
                round
                @click="toggleLayoutType(l.code)"
              >
                {{ l.label }}
              </van-tag>
            </div>
          </div>

          <!-- 租期 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">租期</div>
            <div class="flex flex-wrap gap-2">
              <van-tag
                v-for="t in leaseTerms"
                :key="t.code"
                :type="filter.lease_terms.includes(t.code) ? 'primary' : 'default'"
                size="large"
                round
                @click="toggleLeaseTerm(t.code)"
              >
                {{ t.label }}
              </van-tag>
            </div>
          </div>

          <!-- 价格区间 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">价格区间（元/月）</div>
            <div class="flex items-center gap-2">
              <van-field
                v-model.number="filter.min_price"
                type="digit"
                placeholder="最低"
                class="flex-1"
              />
              <span class="text-gray-400">-</span>
              <van-field
                v-model.number="filter.max_price"
                type="digit"
                placeholder="最高"
                class="flex-1"
              />
            </div>
          </div>

          <!-- 地铁 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">地铁</div>
            <div class="flex flex-wrap gap-2">
              <van-tag
                v-for="line in metroLines"
                :key="line.id"
                :type="selectedMetroLineId === line.id ? 'primary' : 'default'"
                size="large"
                round
                @click="selectMetroLine(line)"
              >
                {{ line.name }}
              </van-tag>
            </div>
            <div v-if="selectedMetroLineId !== null && metroStations.length > 0" class="mt-3">
              <div class="text-xs text-gray-500 mb-2">选择站点（多选）</div>
              <div class="flex flex-wrap gap-2">
                <van-tag
                  v-for="station in metroStations"
                  :key="station.id"
                  :type="filter.metro_station_ids.includes(station.id) ? 'primary' : 'default'"
                  size="medium"
                  round
                  @click="toggleMetroStation(station.id)"
                >
                  {{ station.name }}
                </van-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="flex gap-3 p-4 border-t border-gray-100 safe-area-bottom">
          <van-button class="flex-1" @click="onFilterReset">重置</van-button>
          <van-button type="primary" class="flex-1" @click="onFilterConfirm">确定</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.apartment-list {
  min-height: 100vh;
  background-color: $bg-color;
}

.map-view-wrapper {
  height: calc(100vh - 140px);
}

.apartment-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.apartment-card {
  display: flex;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.apartment-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-image {
  width: 112px;
  height: 112px;
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  padding: 12px;
}

@media (min-width: 768px) {
  .apartment-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    padding: 16px 24px;
  }

  .apartment-card {
    flex-direction: column;
  }

  .card-image {
    width: 100%;
    height: 180px;
  }

  .card-info {
    padding: 14px;
  }
}

@media (min-width: 1280px) {
  .apartment-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .card-image {
    height: 200px;
  }
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-state {
  padding-top: 20vh;
}

.text-warning {
  color: $warning;
}

.drop-shadow {
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
}

:deep(.van-search) {
  padding: 0;
}

:deep(.van-field) {
  background-color: #f7f8fa;
  border-radius: 8px;
}

.fixed-fab {
  position: fixed;
  right: 24px;
  bottom: 80px;
  z-index: 999;
  cursor: pointer;
}

.compare-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 998;
  background-color: #fff;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.compare-count {
  font-size: 14px;
  color: #323233;
}

.has-compare-bar {
  padding-bottom: 64px;
}

.select-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.35);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.select-indicator.active {
  background-color: $primary;
}

.card-selected {
  box-shadow: 0 0 0 2px $primary;
}
</style>
