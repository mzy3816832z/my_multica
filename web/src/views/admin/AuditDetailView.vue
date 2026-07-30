<script setup lang="ts">
import { formatDateTime } from '@/utils/datetime'
import {
  layoutTypeMap,
  windowTypeMap,
  facilityMap,
  leaseTermMap,
  paymentMethodMap,
  mapDict,
  mapFacilities,
} from '@/utils/dictMaps'
import { getDistrictName, getStreetName } from '@/utils/districtMaps'
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getAdminAuditDetail, approveAudit, rejectAudit } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import type { AuditRecord } from '@/types'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()

const auditId = ref(Number(route.params.id))
const detail = ref<AuditRecord | null>(null)
const loading = ref(false)
const rejectReason = ref('')
const showRejectForm = ref(false)

async function loadDetail() {
  loading.value = true
  try {
    const res = await getAdminAuditDetail(auditId.value)
    detail.value = res
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.back()
}

// 通过
async function onApprove() {
  try {
    await showConfirmDialog({
      title: '确认通过',
      message: '审核通过后，房源将正式上架或变更生效，确定继续吗？',
    })
    uiStore.showLoading('处理中...')
    await approveAudit(auditId.value)
    showToast('已通过')
    await loadDetail()
  } catch (err: any) {
    if (err?.message === 'cancel') {
      // 用户取消
    }
  } finally {
    uiStore.hideLoading()
  }
}

// 显示驳回表单
function onShowReject() {
  if (detail.value?.status !== 'pending') {
    showToast('当前状态不可驳回')
    return
  }
  showRejectForm.value = true
}

// 确认驳回
async function onConfirmReject() {
  if (!rejectReason.value.trim()) {
    showToast('请填写驳回原因')
    return
  }
  try {
    uiStore.showLoading('处理中...')
    await rejectAudit(auditId.value, rejectReason.value.trim())
    showToast('已驳回')
    showRejectForm.value = false
    rejectReason.value = ''
    await loadDetail()
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
}

function auditTypeText(type?: string) {
  return type === 'first_review' ? '提交审核' : '变更审核'
}

function auditStatusText(status?: string) {
  const map: Record<string, string> = {
    pending: '待审核',
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

// 判断字段是否变更
function isChangedField(field: string): boolean {
  return detail.value?.changed_fields?.includes(field) ?? false
}

// 获取字段样式
function fieldClass(field: string): string {
  return isChangedField(field) ? 'text-danger font-bold' : 'text-gray-900'
}

// 格式化展示对象
function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'string') return val
  if (typeof val === 'number') return String(val)
  if (typeof val === 'boolean') return val ? '是' : '否'
  if (Array.isArray(val)) {
    if (val.length === 0) return '-'
    return val.map((v) => formatValue(v)).join('、')
  }
  if (typeof val === 'object') {
    return JSON.stringify(val)
  }
  return String(val)
}

// 提取房源基础信息字段
const baseFields = [
  { key: 'name', label: '房源名称' },
  { key: 'description', label: '房源描述' },
  { key: 'district_id', label: '行政区', format: (v: unknown) => getDistrictName(Number(v)) },
  { key: 'street_id', label: '街道', format: (v: unknown) => getStreetName(Number(v)) },
  { key: 'detail_address', label: '详细地址' },
  { key: 'contact_phone', label: '联系电话' },
]

watch(() => route.params.id, (newId) => {
  const id = Number(newId)
  if (id && !isNaN(id) && id !== auditId.value) {
    auditId.value = id
    loadDetail()
  }
})

onMounted(() => {
  loadDetail()
})
</script>

<template>
  <div class="audit-detail-page">
    <van-nav-bar title="审核详情" left-arrow @click-left="goBack" fixed placeholder />

    <div v-if="loading" class="flex justify-center items-center pt-20">
      <van-loading type="spinner" size="24" />
    </div>

    <div v-else-if="!detail" class="pt-20">
      <van-empty description="审核记录不存在" />
    </div>

    <div v-else class="pb-24">
      <!-- 基本信息卡片 -->
      <div class="bg-white m-3 rounded-xl overflow-hidden shadow-sm">
        <div class="flex p-3 gap-3">
          <van-image
            :src="(detail.submitted_data as any)?.cover_image || ''"
            fit="cover"
            class="w-24 h-24 rounded-lg flex-shrink-0"
          />
          <div class="flex-1 min-w-0 flex flex-col justify-between">
            <div>
              <div class="text-sm font-bold text-gray-900 truncate">
                {{ (detail.submitted_data as any)?.name || '-' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">
                {{ auditTypeText(detail.type) }}
              </div>
              <div v-if="detail.changed_fields && detail.changed_fields.length > 0" class="text-xs text-danger mt-0.5">
                变更字段：{{ detail.changed_fields.join('、') }}
              </div>
              <div class="text-xs text-gray-400 mt-0.5">
                提交时间：{{ formatDateTime(detail.created_at) }}
              </div>
            </div>
            <div class="flex items-center justify-between mt-2">
              <van-tag :type="auditStatusType(detail.status)" size="medium" round>
                {{ auditStatusText(detail.status) }}
              </van-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 提交数据详情 -->
      <div class="bg-white m-3 rounded-xl overflow-hidden shadow-sm">
        <div class="px-4 py-3 border-b border-gray-100 font-bold text-sm">提交信息</div>
        <van-cell-group :border="false">
          <van-cell
            v-for="f in baseFields"
            :key="f.key"
            :title="f.label"
            :class="isChangedField(f.key) ? 'changed-field' : ''"
          >
            <template #value>
              <span :class="fieldClass(f.key)">
                {{ f.format ? f.format((detail.submitted_data as any)?.[f.key]) : formatValue((detail.submitted_data as any)?.[f.key]) }}
              </span>
            </template>
          </van-cell>
        </van-cell-group>
      </div>

      <!-- 房型信息 -->
      <div
        v-if="(detail.submitted_data as any)?.room_types && (detail.submitted_data as any)?.room_types.length > 0"
        class="bg-white m-3 rounded-xl overflow-hidden shadow-sm"
      >
        <div class="px-4 py-3 border-b border-gray-100 font-bold text-sm">房型信息</div>
        <div
          v-for="(room, idx) in (detail.submitted_data as any)?.room_types"
          :key="idx"
          class="p-3 border-b border-gray-100 last:border-b-0"
        >
          <div class="text-sm font-bold mb-2">房型 {{ (idx as number) + 1 }}：{{ room.name || '-' }}</div>
          <div class="space-y-1 text-xs">
            <div :class="isChangedField('room_types') ? 'text-danger font-bold' : 'text-gray-700'">
              <span class="text-gray-500">布局：</span>{{ mapDict(room.layout_type_label || room.layout_type, layoutTypeMap) }}
            </div>
            <div :class="isChangedField('room_types') ? 'text-danger font-bold' : 'text-gray-700'">
              <span class="text-gray-500">窗户：</span>{{ mapDict(room.window_type_label || room.window_type, windowTypeMap) }}
            </div>
            <div :class="isChangedField('room_types') ? 'text-danger font-bold' : 'text-gray-700'">
              <span class="text-gray-500">楼层：</span>{{ room.floor ?? '-' }}
            </div>
            <div :class="isChangedField('room_types') ? 'text-danger font-bold' : 'text-gray-700'">
              <span class="text-gray-500">设施：</span>{{ mapFacilities(room.facilities) }}
            </div>
            <div :class="isChangedField('room_types') ? 'text-danger font-bold' : 'text-gray-700'">
              <div class="text-gray-500 mb-1">租金方案：</div>
              <div
                v-for="(plan, pidx) in room.rental_plans"
                :key="pidx"
                class="pl-2 mb-2 pb-2 border-b border-gray-100 last:border-b-0"
              >
                <div><span class="text-gray-500">租期：</span>{{ mapDict(plan.lease_term_label || plan.lease_term, leaseTermMap) }}</div>
                <div><span class="text-gray-500">月租金：</span>{{ plan.monthly_rent }} 元</div>
                <div><span class="text-gray-500">支付方式：</span>{{ mapDict(plan.payment_method_label || plan.payment_method, paymentMethodMap) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 驳回原因（如已驳回） -->
      <div v-if="detail.status === 'rejected' && detail.reject_reason" class="bg-white m-3 rounded-xl overflow-hidden shadow-sm">
        <div class="px-4 py-3 border-b border-gray-100 font-bold text-sm text-danger">驳回原因</div>
        <div class="p-3 text-sm text-danger">
          {{ detail.reject_reason }}
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div v-if="detail.status === 'pending' && !showRejectForm" class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-3 flex gap-3 safe-area-bottom">
        <van-button type="danger" block round plain class="flex-1" @click="onShowReject">
          驳回
        </van-button>
        <van-button type="success" block round class="flex-1" @click="onApprove">
          通过
        </van-button>
      </div>

      <!-- 驳回表单 -->
      <div v-if="showRejectForm" class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-3 safe-area-bottom">
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
    </div>
  </div>
</template>

<style scoped lang="scss">
.audit-detail-page {
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

.changed-field {
  :deep(.van-cell__title) {
    color: $danger;
    font-weight: bold;
  }
}

.safe-area-bottom {
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
}
</style>
