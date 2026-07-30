<script setup lang="ts">
import { formatDateTime } from '@/utils/datetime'
import { auditTypeMap, auditStatusMap } from '@/utils/dictMaps'
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { getAdminAudits, approveAudit, rejectAudit } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import type { AuditRecord } from '@/types'

const router = useRouter()
const uiStore = useUiStore()

const activeTab = ref(0)
const tabNames = ['全部', '提交审核', '变更审核']
const tabTypes: (undefined | 'first_review' | 'change_review')[] = [undefined, 'first_review', 'change_review']

const list = ref<AuditRecord[]>([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const PAGE_SIZE = 10

const keyword = ref('')

// 驳回弹框相关状态
const showRejectForm = ref(false)
const rejectReason = ref('')
const rejectTargetId = ref<number | null>(null)

// 加载列表
async function loadList(isRefresh = false) {
  if (isRefresh) {
    page.value = 1
    finished.value = false
  }
  if (finished.value) return

  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: PAGE_SIZE,
      type: tabTypes[activeTab.value],
    }
    if (keyword.value.trim()) {
      params.keyword = keyword.value.trim()
    }
    const data = await getAdminAudits(params)
    if (isRefresh) {
      list.value = data.items
    } else {
      list.value.push(...data.items)
    }
    page.value++
    if (list.value.length >= data.total) {
      finished.value = true
    }
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function onRefresh() {
  loadList(true)
}

function onLoad() {
  loadList()
}

function onTabChange() {
  loadList(true)
}

function onSearch() {
  loadList(true)
}

function goBack() {
  router.back()
}

function goDetail(id: number) {
  router.push('/admin/audits/' + id)
}

// 快捷通过
async function onQuickApprove(id: number) {
  try {
    await showConfirmDialog({
      title: '确认通过',
      message: '审核通过后，房源将正式上架或变更生效，确定继续吗？',
    })
    uiStore.showLoading('处理中...')
    await approveAudit(id)
    showToast('已通过')
    loadList(true)
  } catch (err: any) {
    if (err?.message === 'cancel') {
      // 用户取消
    }
  } finally {
    uiStore.hideLoading()
  }
}

// 显示驳回弹框
function onShowReject(id: number) {
  rejectTargetId.value = id
  rejectReason.value = ''
  showRejectForm.value = true
}

// 确认驳回
async function onConfirmReject() {
  if (!rejectReason.value.trim()) {
    showToast('请填写驳回原因')
    return
  }
  if (!rejectTargetId.value) return
  try {
    uiStore.showLoading('处理中...')
    await rejectAudit(rejectTargetId.value, rejectReason.value.trim())
    showToast('已驳回')
    showRejectForm.value = false
    rejectReason.value = ''
    rejectTargetId.value = null
    loadList(true)
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    uiStore.hideLoading()
  }
}

// 取消驳回
function onCancelReject() {
  showRejectForm.value = false
  rejectReason.value = ''
  rejectTargetId.value = null
}

function auditTypeText(type?: string) {
  return auditTypeMap[type || ''] || type || '-'
}

function auditStatusText(status?: string) {
  return auditStatusMap[status || ''] || status || '-'
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
  loadList(true)
})
</script>

<template>
  <div class="audit-list-page">
    <van-nav-bar title="审核管理" left-arrow @click-left="goBack" fixed placeholder />

    <!-- 搜索栏 -->
    <div class="sticky top-[46px] z-10 bg-bg">
      <van-search
        v-model="keyword"
        placeholder="搜索房源名称"
        shape="round"
        @search="onSearch"
        @clear="onSearch"
        class="px-4 py-2"
      />
    </div>

    <van-tabs v-model:active="activeTab" sticky offset-top="100" class="audit-tabs" @change="onTabChange">
      <van-tab v-for="(name, idx) in tabNames" :key="idx" :title="name">
        <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
          <van-list
            v-model:loading="loading"
            :finished="finished"
            finished-text="没有更多了"
            @load="onLoad"
          >
            <!-- 空状态 -->
            <van-empty v-if="list.length === 0 && !loading" description="暂无审核记录" />

            <!-- 审核卡片列表 -->
            <div v-else class="p-3 space-y-3">
              <div
                v-for="item in list"
                :key="item.id"
                class="bg-white rounded-xl overflow-hidden shadow-sm"
                @click="goDetail(item.id)"
              >
                <div class="flex p-3 gap-3">
                  <van-image
                    :src="item.cover_image || ''"
                    fit="cover"
                    class="w-24 h-24 rounded-lg flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <div class="text-sm font-bold text-gray-900 truncate">
                        {{ item.apartment_name || '-' }}
                      </div>
                      <div class="text-xs text-gray-500 mt-1">
                        {{ auditTypeText(item.type) }}
                      </div>
                      <div v-if="item.changed_fields && item.changed_fields.length > 0" class="text-xs text-danger mt-0.5">
                        变更字段：{{ item.changed_fields.join('、') }}
                      </div>
                      <div class="text-xs text-gray-400 mt-0.5">
                        提交时间：{{ formatDateTime(item.created_at) }}
                      </div>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                      <van-tag :type="auditStatusType(item.status)" size="medium" round>
                        {{ auditStatusText(item.status) }}
                      </van-tag>
                    </div>
                  </div>
                </div>

                <!-- 快捷操作（仅待审核） -->
                <div v-if="item.status === 'pending'" class="flex border-t border-gray-100">
                  <div
                    class="flex-1 py-2.5 text-center text-sm text-success flex items-center justify-center gap-1"
                    @click.stop="onQuickApprove(item.id)"
                  >
                    <van-icon name="success" />
                    <span>通过</span>
                  </div>
                  <div class="w-px bg-gray-100" />
                  <div
                    class="flex-1 py-2.5 text-center text-sm text-danger flex items-center justify-center gap-1"
                    @click.stop="onShowReject(item.id)"
                  >
                    <van-icon name="close" />
                    <span>驳回</span>
                  </div>
                </div>
              </div>
            </div>
          </van-list>
        </van-pull-refresh>
      </van-tab>
    </van-tabs>
    <!-- 驳回弹框 -->
    <van-popup v-model:show="showRejectForm" position="bottom" round :style="{ maxHeight: '60%' }">
      <div class="p-4">
        <div class="text-sm font-bold mb-2">驳回原因（必填）</div>
        <van-field
          v-model="rejectReason"
          type="textarea"
          placeholder="请填写驳回原因，商家将收到此消息..."
          rows="3"
          maxlength="200"
          show-word-limit
          class="mb-3"
        />
        <div class="flex gap-3">
          <van-button block round plain class="flex-1" @click="onCancelReject">取消</van-button>
          <van-button type="danger" block round class="flex-1" @click="onConfirmReject">确认驳回</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.audit-list-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.text-danger {
  color: $danger;
}

.text-success {
  color: $success;
}

.text-primary {
  color: $primary;
}

.audit-tabs {
  :deep(.van-tabs__wrap) {
    background-color: #fff;
  }
}
</style>
