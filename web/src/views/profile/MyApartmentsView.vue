<script setup lang="ts">
import { formatDateTime } from '@/utils/datetime'
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMerchantApartments, getMerchantAudits, deleteApartment } from '@/api/merchant'
import { useUiStore } from '@/stores/ui'
import type { Apartment, MerchantAuditItem } from '@/types'

const router = useRouter()
const uiStore = useUiStore()

const activeTab = ref(0)

// 已上架房源
const publishedList = ref<Apartment[]>([])
const publishedLoading = ref(false)
const publishedFinished = ref(false)
const publishedRefreshing = ref(false)
const publishedPage = ref(1)
const PAGE_SIZE = 10

// 审核中
const auditList = ref<MerchantAuditItem[]>([])
const auditLoading = ref(false)
const auditFinished = ref(false)
const auditRefreshing = ref(false)
const auditPage = ref(1)

// 加载已上架房源
async function loadPublishedList(isRefresh = false) {
  if (isRefresh) {
    publishedPage.value = 1
    publishedFinished.value = false
  }
  if (publishedFinished.value) return

  publishedLoading.value = true
  try {
    const data = await getMerchantApartments({ page: publishedPage.value, page_size: PAGE_SIZE })
    if (isRefresh) {
      publishedList.value = data.items
    } else {
      publishedList.value.push(...data.items)
    }
    publishedPage.value++
    if (publishedList.value.length >= data.total) {
      publishedFinished.value = true
    }
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    publishedLoading.value = false
    publishedRefreshing.value = false
  }
}

// 加载审核中列表（后端按 created_at 倒序返回）
async function loadAuditList(isRefresh = false) {
  if (isRefresh) {
    auditPage.value = 1
    auditFinished.value = false
  }
  if (auditFinished.value) return

  auditLoading.value = true
  try {
    const data = await getMerchantAudits({ page: auditPage.value, page_size: PAGE_SIZE })
    if (isRefresh) {
      auditList.value = data.items
    } else {
      auditList.value.push(...data.items)
    }
    auditPage.value++
    if (auditList.value.length >= data.total) {
      auditFinished.value = true
    }
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    auditLoading.value = false
    auditRefreshing.value = false
  }
}

// 下拉刷新
function onPublishedRefresh() {
  loadPublishedList(true)
}

function onAuditRefresh() {
  loadAuditList(true)
}

// 加载更多
function onPublishedLoad() {
  loadPublishedList()
}

function onAuditLoad() {
  loadAuditList()
}

// 编辑
function goEdit(id: number) {
  router.push('/profile/apartments/' + id + '/edit')
}

// 删除
async function onDelete(id: number) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '删除后该房源将不可恢复，关联的未审核单据也会同步处理，确定继续吗？',
    })
    uiStore.showLoading('删除中...')
    await deleteApartment(id)
    showToast('删除成功')
    // 刷新列表
    loadPublishedList(true)
    loadAuditList(true)
  } catch (err: any) {
    if (err?.message === 'cancel') {
      // 用户取消
    } else {
      // 错误已在 request 拦截器中 toast
    }
  } finally {
    uiStore.hideLoading()
  }
}

// 状态标签
function statusText(status?: string) {
  const map: Record<string, string> = {
    draft: '草稿',
    pending_first_review: '首次审核中',
    first_rejected: '首次审核驳回',
    published: '已上架',
  }
  return map[status || ''] || status || '-'
}

function statusType(status?: string): 'primary' | 'success' | 'warning' | 'danger' | 'default' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'default'> = {
    draft: 'default',
    pending_first_review: 'warning',
    first_rejected: 'danger',
    published: 'success',
  }
  return map[status || ''] || 'default'
}

// 审核单类型与状态
function auditTypeText(type?: string) {
  return type === 'first_review' ? '首次审核' : '变更审核'
}

function auditStatusText(status?: string) {
  const map: Record<string, string> = {
    pending: '审核中',
    approved: '已通过',
    rejected: '已驳回',
  }
  return map[status || ''] || status || '-'
}

function auditStatusType(status?: string): 'primary' | 'success' | 'warning' | 'danger' | 'default' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'default'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }
  return map[status || ''] || 'default'
}

onMounted(() => {
  loadPublishedList(true)
  loadAuditList(true)
})
</script>

<template>
  <div class="my-apartments-page">
    <van-nav-bar title="已上架房源" left-arrow @click-left="$router.back()" fixed placeholder />

    <van-tabs v-model:active="activeTab" sticky offset-top="46" class="apartment-tabs">
      <van-tab title="已上架">
        <van-pull-refresh v-model="publishedRefreshing" @refresh="onPublishedRefresh">
          <van-list
            v-model:loading="publishedLoading"
            :finished="publishedFinished"
            finished-text="没有更多了"
            @load="onPublishedLoad"
          >
            <!-- 空状态 -->
            <van-empty v-if="publishedList.length === 0 && !publishedLoading" description="暂无已上架房源" />

            <!-- 房源卡片列表 -->
            <div v-else class="p-3 space-y-3">
              <div
                v-for="item in publishedList"
                :key="item.id"
                class="bg-white rounded-xl overflow-hidden shadow-sm"
              >
                <div class="flex p-3 gap-3">
                  <van-image
                    :src="item.cover_image"
                    fit="cover"
                    class="w-24 h-24 rounded-lg flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <div class="text-sm font-bold text-gray-900 truncate">{{ item.name }}</div>
                      <div class="text-xs text-gray-500 mt-1">
                        {{ item.district_name }} {{ item.street_name }}
                      </div>
                      <div class="text-xs text-gray-400 mt-0.5">{{ item.detail_address }}</div>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                      <van-tag :type="statusType(item.status)" size="medium" round>
                        {{ statusText(item.status) }}
                      </van-tag>
                      <span class="text-sm font-bold text-danger">
                        {{ item.min_monthly_rent ? item.min_monthly_rent + ' 元/月起' : '-' }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="flex border-t border-gray-100">
                  <div
                    class="flex-1 py-2.5 text-center text-sm text-primary flex items-center justify-center gap-1"
                    @click="goEdit(item.id)"
                  >
                    <van-icon name="edit" />
                    <span>编辑</span>
                  </div>
                  <div class="w-px bg-gray-100" />
                  <div
                    class="flex-1 py-2.5 text-center text-sm text-danger flex items-center justify-center gap-1"
                    @click="onDelete(item.id)"
                  >
                    <van-icon name="delete-o" />
                    <span>删除</span>
                  </div>
                </div>
              </div>
            </div>
          </van-list>
        </van-pull-refresh>
      </van-tab>

      <van-tab title="审核中">
        <van-pull-refresh v-model="auditRefreshing" @refresh="onAuditRefresh">
          <van-list
            v-model:loading="auditLoading"
            :finished="auditFinished"
            finished-text="没有更多了"
            @load="onAuditLoad"
          >
            <!-- 空状态 -->
            <van-empty v-if="auditList.length === 0 && !auditLoading" description="暂无审核中的房源" />

            <!-- 审核单卡片列表 -->
            <div v-else class="p-3 space-y-3">
              <div
                v-for="item in auditList"
                :key="item.id"
                class="bg-white rounded-xl overflow-hidden shadow-sm"
              >
                <div class="flex p-3 gap-3">
                  <van-image
                    :src="item.cover_image || ''"
                    fit="cover"
                    class="w-24 h-24 rounded-lg flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <div class="text-sm font-bold text-gray-900 truncate">{{ item.apartment_name || '-' }}</div>
                      <div class="text-xs text-gray-500 mt-1">
                        {{ auditTypeText(item.type) }}
                      </div>
                      <div v-if="item.changed_fields && item.changed_fields.length > 0" class="text-xs text-gray-400 mt-0.5">
                        变更字段：{{ item.changed_fields.join('、') }}
                      </div>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                      <van-tag :type="auditStatusType(item.status)" size="medium" round>
                        {{ auditStatusText(item.status) }}
                      </van-tag>
                      <span class="text-xs text-gray-400">{{ formatDateTime(item.created_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </van-list>
        </van-pull-refresh>
      </van-tab>
    </van-tabs>
  </div>
</template>

<style scoped lang="scss">
.my-apartments-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.text-danger {
  color: $danger;
}

.text-primary {
  color: $primary;
}

.apartment-tabs {
  :deep(.van-tabs__wrap) {
    background-color: #fff;
  }
}
</style>
