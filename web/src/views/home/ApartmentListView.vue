<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getApartments } from '@/api/apartment'
import { getDistricts } from '@/api/dict'
import { addFavorite, removeFavorite } from '@/api/favorite'
import type { Apartment, District, DictItem } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

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

// ================= 筛选 =================
const showFilter = ref(false)

const filter = reactive({
  district_id: undefined as number | undefined,
  street_ids: [] as number[],
  layout_types: [] as string[],
  lease_terms: [] as string[],
  min_price: undefined as number | undefined,
  max_price: undefined as number | undefined,
})


// 行政区名称静态映射（仅用于展示名称和排序，真实ID从接口获取）
const districtNameMap = new Map<string, number>([
  ['黄浦区', 1],
  ['静安区', 2],
  ['徐汇区', 3],
  ['长宁区', 4],
  ['普陀区', 5],
  ['虹口区', 6],
  ['杨浦区', 7],
  ['浦东新区', 8],
  ['闵行区', 9],
  ['宝山区', 10],
  ['嘉定区', 11],
  ['金山区', 12],
  ['松江区', 13],
  ['青浦区', 14],
  ['奉贤区', 15],
  ['崇明区', 16],
])

const districts = ref<District[]>([])

// 加载真实行政区数据（带真实ID）
async function loadDistricts() {
  try {
    const res = await getDistricts({ level: 1 })
    // 按 districtNameMap 中的顺序排序，保持前端展示顺序一致
    const sorted = res.sort((a: District, b: District) => {
      const sortA = districtNameMap.get(a.name) || 999
      const sortB = districtNameMap.get(b.name) || 999
      return sortA - sortB
    })
    districts.value = sorted
  } catch {
    // 降级：如果接口失败，保持空数组，不显示行政区
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
  return count
})

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

function onSearch() {
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
  streets.value = []
}

function onFilterClear() {
  onFilterReset()
  onFilterConfirm()
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

// ================= 初始化 =================
onMounted(() => {
  loadDistricts()
  fetchList(true)
})
</script>

<template>
  <div class="apartment-list">
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
    </div>

    <!-- 列表内容 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="list.length === 0 && !loading" class="empty-state">
          <van-empty description="暂无房源" />
        </div>

        <div class="px-3 py-2 space-y-3">
          <div
            v-for="item in list"
            :key="item.id"
            class="flex bg-white rounded-xl overflow-hidden shadow-sm"
            @click="goDetail(item.id)"
          >
            <!-- 左侧图片 -->
            <div class="w-28 h-28 flex-shrink-0 bg-gray-100">
              <van-image
                :src="item.cover_image"
                fit="cover"
                class="w-full h-full"
                :alt="item.name"
              />
            </div>
            <!-- 右侧信息 -->
            <div class="flex-1 p-3 flex flex-col justify-between min-w-0">
              <div>
                <h3 class="text-base font-bold text-gray-900 line-clamp-1">{{ item.name }}</h3>
                <p class="text-sm text-gray-500 mt-1 flex items-center">
                  <van-icon name="location-o" class="mr-1" />
                  {{ item.district_name || '' }} {{ item.street_name || '' }}
                </p>
              </div>
              <div class="flex items-center justify-between mt-2">
                <span v-if="item.min_monthly_rent != null" class="text-primary font-bold">¥{{ item.min_monthly_rent }}/月起</span>
                <span v-else class="text-sm text-gray-400">暂无报价</span>
                <van-icon
                  v-if="authStore.isTenant"
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

    <!-- 商家悬浮发布按钮 -->
    <van-floating-bubble
      v-if="authStore.isLandlord"
      axis="xy"
      magnetic="x"
      :offset="{ x: 320, y: 500 }"
      @click="goCreate"
    >
      <div class="w-12 h-12 bg-primary rounded-full flex items-center justify-center shadow-lg">
        <van-icon name="plus" class="text-white text-xl" />
      </div>
    </van-floating-bubble>

    <!-- 搜索弹窗 -->
    <van-popup v-model:show="showSearch" position="top" :style="{ height: '100%' }" class="bg-white">
      <div class="flex items-center px-3 py-2 border-b border-gray-100">
        <van-search
          v-model="keyword"
          placeholder="搜索房源名称"
          show-action
          class="flex-1"
          @search="onSearch"
        >
          <template #action>
            <span class="text-primary text-sm" @click="onSearch">搜索</span>
          </template>
        </van-search>
        <span class="text-sm text-gray-500 ml-2" @click="showSearch = false">取消</span>
      </div>
      <div class="p-4 text-sm text-gray-400">
        输入关键词后点击搜索
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

:deep(.van-floating-bubble) {
  --van-floating-bubble-background: transparent;
}
</style>
