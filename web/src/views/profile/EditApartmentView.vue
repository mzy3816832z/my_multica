<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { getMerchantApartmentDetail, updateApartment } from '@/api/merchant'
import { useApartmentForm } from '@/composables/useApartmentForm'
import { mapDict, layoutTypeMap } from '@/utils/dictMaps'
import type { RoomType, RentalPlan } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

const apartmentId = ref(Number(route.params.id))

const {
  form,
  formErrors,
  roomFormErrors,
  rentalPlanErrors,
  districtValue,
  coverUploader,
  uploadingCover,
  triggerCoverUpload,
  onCoverChange,
  removeCover,
  showRoomModal,
  isEditingRoom,
  roomForm,
  roomImageUploader,
  uploadingRoomImage,
  pendingRoomImages,
  openAddRoom,
  openEditRoom,
  closeRoomModal,
  triggerRoomImageUpload,
  onRoomImageChange,
  retryRoomImage,
  removePendingRoomImage,
  removeRoomImage,
  dragIndex,
  dragOverIndex,
  onDragStart,
  onDragOver,
  onDrop,
  addRentalPlan,
  removeRentalPlan,
  saveRoom,
  removeRoomType,
  canSubmit,
  validateForm,
  buildPayload,
} = useApartmentForm()

const districtModel = computed({
  get: () => ({
    district_id: form.district_id,
    street_id: form.street_id,
  }),
  set: (val) => {
    form.district_id = val?.district_id
    form.street_id = val?.street_id
  },
})

const loadingDetail = ref(false)

async function loadApartmentDetail() {
  if (!apartmentId.value) return
  loadingDetail.value = true
  try {
    const data = await getMerchantApartmentDetail(apartmentId.value)
    form.name = data.name
    form.cover_image = data.cover_image
    form.description = data.description || ''
    form.district_id = data.district_id
    form.street_id = data.street_id
    form.detail_address = data.detail_address || ''
    form.contact_phone = data.contact_phone || ''
    form.property_fee = data.property_fee ?? undefined
    form.water_fee = data.water_fee || ''
    form.electric_fee = data.electric_fee || ''
    form.service_fee = data.service_fee ?? undefined
    form.other_fees = data.other_fees || ''
    form.room_types = (data.room_types || []).map((r: RoomType) => ({
      id: r.id,
      name: r.name,
      images: [...r.images],
      facilities: [...r.facilities],
      layout_type: r.layout_type,
      window_type: r.window_type,
      floor: r.floor,
      area: (r as any).area !== undefined && (r as any).area !== null ? Number((r as any).area) : undefined,
      orientation: (r as any).orientation || '',
      available_date: (r as any).available_date || '',
      rental_plans: (r.rental_plans || []).map((p: RentalPlan) => ({
        lease_term: p.lease_term,
        monthly_rent: p.monthly_rent,
        payment_method: p.payment_method,
      })),
    }))
  } catch {
  } finally {
    loadingDetail.value = false
  }
}

async function onSubmit() {
  if (!validateForm()) {
    showToast('请完善公寓信息')
    return
  }

  uiStore.showLoading('保存中...')
  try {
    await updateApartment(apartmentId.value, buildPayload() as any)
    showToast('保存成功')
    router.replace('/profile/my-apartments')
  } catch {
  } finally {
    uiStore.hideLoading()
  }
}

watch(() => route.params.id, (newId) => {
  const id = Number(newId)
  if (id && !isNaN(id) && id !== apartmentId.value) {
    apartmentId.value = id
    loadApartmentDetail()
  }
})

onMounted(() => {
  loadApartmentDetail()
})
</script>

<template>
  <div class="edit-apartment-page">
    <van-nav-bar title="编辑房源" left-arrow @click-left="router.back()" fixed placeholder />

    <div v-if="loadingDetail" class="flex items-center justify-center py-20">
      <van-loading type="spinner" color="#1989fa" />
    </div>

    <div v-else class="form-container">
      <div class="p-4 space-y-4">
      <!-- 公寓名称 -->
      <div class="bg-white rounded-xl p-4">
        <div class="text-sm font-bold text-gray-900 mb-2">公寓名称 <span class="text-danger">*</span></div>
        <van-field
          v-model="form.name"
          placeholder="请输入公寓名称（最多50字）"
          maxlength="50"
          show-word-limit
          :border="false"
          class="bg-gray-50 rounded-lg"
        />
        <div v-if="formErrors.name" class="text-danger text-xs mt-1">{{ formErrors.name }}</div>
      </div>

      <!-- 总览图上传 -->
      <div class="bg-white rounded-xl p-4">
        <div class="text-sm font-bold text-gray-900 mb-2">公寓总览图 <span class="text-danger">*</span></div>
        <div v-if="form.cover_image" class="relative w-full h-44 rounded-lg overflow-hidden">
          <van-image :src="form.cover_image" fit="cover" class="w-full h-full" />
          <div class="absolute top-2 right-2 w-7 h-7 bg-black/50 rounded-full flex items-center justify-center" @click="removeCover">
            <van-icon name="cross" class="text-white text-sm" />
          </div>
        </div>
        <div
          v-else
          class="w-full h-44 bg-gray-50 rounded-lg flex flex-col items-center justify-center border border-dashed border-gray-300"
          @click="triggerCoverUpload"
        >
          <van-icon v-if="uploadingCover" name="loading" class="text-primary text-2xl animate-spin" />
          <template v-else>
            <van-icon name="photograph" class="text-gray-400 text-2xl mb-2" />
            <span class="text-sm text-gray-400">点击上传总览图</span>
          </template>
        </div>
        <input ref="coverUploader" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="onCoverChange" />
        <div v-if="formErrors.cover_image" class="text-danger text-xs mt-1">{{ formErrors.cover_image }}</div>
      </div>

      <!-- 公寓描述 -->
      <div class="bg-white rounded-xl p-4">
        <div class="text-sm font-bold text-gray-900 mb-2">公寓描述 <span class="text-danger">*</span></div>
        <van-field
          v-model="form.description"
          type="textarea"
          rows="4"
          placeholder="请输入公寓描述（不超过500字）"
          maxlength="500"
          show-word-limit
          :border="false"
          class="bg-gray-50 rounded-lg"
        />
        <div v-if="formErrors.description" class="text-danger text-xs mt-1">{{ formErrors.description }}</div>
      </div>

      <!-- 所在位置 -->
      <div class="bg-white rounded-xl p-4 space-y-3">
        <div class="text-sm font-bold text-gray-900">所在位置 <span class="text-danger">*</span></div>
        <DistrictCascader v-model="districtModel" />
        <div v-if="formErrors.district_id" class="text-danger text-xs mt-1">{{ formErrors.district_id }}</div>
        <div v-if="formErrors.street_id" class="text-danger text-xs mt-1">{{ formErrors.street_id }}</div>
        <van-field
          v-model="form.detail_address"
          placeholder="请输入详细门牌号"
          :border="false"
          class="bg-gray-50 rounded-lg"
        />
        <div v-if="formErrors.detail_address" class="text-danger text-xs mt-1">{{ formErrors.detail_address }}</div>
      </div>

      <!-- 联系电话 -->
      <div class="bg-white rounded-xl p-4">
        <div class="text-sm font-bold text-gray-900 mb-2">联系电话 <span class="text-danger">*</span></div>
        <van-field
          v-model="form.contact_phone"
          type="tel"
          placeholder="请输入联系电话"
          maxlength="11"
          :border="false"
          class="bg-gray-50 rounded-lg"
        />
        <div v-if="formErrors.contact_phone" class="text-danger text-xs mt-1">{{ formErrors.contact_phone }}</div>
      </div>

      <!-- 费用信息（选填） -->
      <div class="bg-white rounded-xl p-4 space-y-3">
        <div class="text-sm font-bold text-gray-900">费用信息</div>

        <div>
          <div class="text-sm text-gray-600 mb-1">物业费（元/月）</div>
          <van-field
            v-model.number="form.property_fee"
            type="digit"
            placeholder="请输入物业费（0 表示免物业费）"
            :border="false"
            class="bg-gray-50 rounded-lg"
          />
        </div>

        <div>
          <div class="text-sm text-gray-600 mb-1">水费</div>
          <DictSelect category="fee_type" v-model="form.water_fee" placeholder="请选择水费类型" title="选择水费类型" />
        </div>

        <div>
          <div class="text-sm text-gray-600 mb-1">电费</div>
          <DictSelect category="fee_type" v-model="form.electric_fee" placeholder="请选择电费类型" title="选择电费类型" />
        </div>

        <div>
          <div class="text-sm text-gray-600 mb-1">服务费（元/月）</div>
          <van-field
            v-model.number="form.service_fee"
            type="digit"
            placeholder="请输入服务费"
            :border="false"
            class="bg-gray-50 rounded-lg"
          />
        </div>

        <div>
          <div class="text-sm text-gray-600 mb-1">其他费用</div>
          <van-field
            v-model="form.other_fees"
            placeholder="请输入其他费用说明（不超过100字）"
            maxlength="100"
            show-word-limit
            :border="false"
            class="bg-gray-50 rounded-lg"
          />
          <div v-if="formErrors.other_fees" class="text-danger text-xs mt-1">{{ formErrors.other_fees }}</div>
        </div>
      </div>

      <!-- 房型列表 -->
      <div class="bg-white rounded-xl p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="text-sm font-bold text-gray-900">房型 <span class="text-danger">*</span></div>
          <span class="text-xs text-gray-400">至少添加 1 组</span>
        </div>

        <div v-if="form.room_types.length > 0" class="space-y-3 mb-3">
          <div
            v-for="(room, index) in form.room_types"
            :key="index"
            class="bg-gray-50 rounded-lg p-3 flex items-center gap-3"
          >
            <van-image
              :src="room.images[0]"
              fit="cover"
              class="w-16 h-16 rounded-lg flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-bold text-gray-900 truncate">{{ room.name }}</div>
              <div class="text-xs text-gray-500 mt-1">
                {{ mapDict(room.layout_type, layoutTypeMap) }} ·
                {{ room.floor }}层 ·
                {{ room.rental_plans.length }} 组方案
              </div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <van-icon name="edit" class="text-primary text-lg" @click="openEditRoom(index)" />
              <van-icon name="delete-o" class="text-danger text-lg" @click="removeRoomType(index)" />
            </div>
          </div>
        </div>

        <van-button type="primary" plain block round icon="plus" @click="openAddRoom">
          添加房型
        </van-button>
        <div v-if="formErrors.room_types" class="text-danger text-xs mt-2">{{ formErrors.room_types }}</div>
      </div>

      <!-- 提交按钮 -->
      <div class="pt-2 pb-6">
        <van-button type="primary" block round :disabled="!canSubmit" @click="onSubmit">
          保存修改
        </van-button>
      </div>
      </div>
    </div>

    <!-- 房型弹窗 -->
    <van-popup v-model:show="showRoomModal" position="bottom" round :style="{ height: '90%' }" class="room-modal">
      <div class="flex flex-col h-full">
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <span class="text-base font-bold">{{ isEditingRoom ? '编辑房型' : '添加房型' }}</span>
          <van-icon name="cross" class="text-gray-400 text-lg" @click="closeRoomModal" />
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <!-- 房型名称 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">房型名称 <span class="text-danger">*</span></div>
            <van-field
              v-model="roomForm.name"
              placeholder="如：标准单间、豪华套房"
              maxlength="50"
              :border="false"
              class="bg-gray-50 rounded-lg"
            />
            <div v-if="roomFormErrors.name" class="text-danger text-xs mt-1">{{ roomFormErrors.name }}</div>
          </div>

          <!-- 房型图片 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">
              房型图片 <span class="text-danger">*</span>
              <span class="text-xs text-gray-400 font-normal">（最多 5 张，支持拖拽排序）</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(img, idx) in roomForm.images"
                :key="'img-' + idx"
                :class="[
                  'relative w-20 h-20 rounded-lg overflow-hidden',
                  dragOverIndex === idx ? 'ring-2 ring-primary' : '',
                  dragIndex === idx ? 'opacity-50' : '',
                ]"
                :draggable="true"
                @dragstart="onDragStart(idx)"
                @dragover.prevent="onDragOver(idx)"
                @drop="onDrop(idx)"
                @dragend="dragIndex = -1; dragOverIndex = -1"
              >
                <van-image :src="img" fit="cover" class="w-full h-full" />
                <div class="absolute top-1 right-1 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center" @click="removeRoomImage(idx)">
                  <van-icon name="cross" class="text-white text-xs" />
                </div>
              </div>
              <div
                v-for="(pending, pIdx) in pendingRoomImages"
                :key="'pending-' + pIdx"
                class="relative w-20 h-20 rounded-lg overflow-hidden border-2"
                :class="pending.status === 'failed' ? 'border-danger' : 'border-primary'"
              >
                <van-icon v-if="pending.status === 'uploading'" name="loading" class="absolute inset-0 m-auto text-primary animate-spin" size="24" />
                <template v-else>
                  <div class="w-full h-full bg-gray-100 flex flex-col items-center justify-center gap-1">
                    <span class="text-danger text-xs text-center px-1">上传失败</span>
                    <span class="text-primary text-xs" @click="retryRoomImage(pending)">重试</span>
                  </div>
                  <div class="absolute top-1 right-1 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center" @click="removePendingRoomImage(pIdx)">
                    <van-icon name="cross" class="text-white text-xs" />
                  </div>
                </template>
              </div>
              <div
                v-if="roomForm.images.length + pendingRoomImages.length < 5"
                class="w-20 h-20 bg-gray-50 rounded-lg flex flex-col items-center justify-center border border-dashed border-gray-300"
                @click="triggerRoomImageUpload"
              >
                <van-icon v-if="uploadingRoomImage" name="loading" class="text-primary animate-spin" />
                <template v-else>
                  <van-icon name="photograph" class="text-gray-400 text-lg" />
                  <span class="text-xs text-gray-400 mt-1">上传</span>
                </template>
              </div>
            </div>
            <input ref="roomImageUploader" type="file" accept="image/jpeg,image/png,image/webp" multiple class="hidden" @change="onRoomImageChange" />
            <div v-if="roomFormErrors.images" class="text-danger text-xs mt-1">{{ roomFormErrors.images }}</div>
          </div>

          <!-- 户型 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">户型 <span class="text-danger">*</span></div>
            <DictSelect category="layout_type" v-model="roomForm.layout_type" title="选择户型" placeholder="请选择户型" />
            <div v-if="roomFormErrors.layout_type" class="text-danger text-xs mt-1">{{ roomFormErrors.layout_type }}</div>
          </div>

          <!-- 窗户类型 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">窗户类型 <span class="text-danger">*</span></div>
            <DictSelect category="window_type" v-model="roomForm.window_type" title="选择窗户类型" placeholder="请选择窗户类型" />
            <div v-if="roomFormErrors.window_type" class="text-danger text-xs mt-1">{{ roomFormErrors.window_type }}</div>
          </div>

          <!-- 楼层 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">楼层 <span class="text-danger">*</span></div>
            <van-field
              v-model.number="roomForm.floor"
              type="digit"
              placeholder="请输入楼层"
              :border="false"
              class="bg-gray-50 rounded-lg"
            />
            <div v-if="roomFormErrors.floor" class="text-danger text-xs mt-1">{{ roomFormErrors.floor }}</div>
          </div>

          <!-- 面积 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">面积 <span class="text-danger">*</span></div>
            <van-field
              v-model.number="roomForm.area"
              type="digit"
              placeholder="请输入面积（0.5-500 ㎡）"
              :border="false"
              class="bg-gray-50 rounded-lg"
            />
            <div v-if="roomFormErrors.area" class="text-danger text-xs mt-1">{{ roomFormErrors.area }}</div>
          </div>

          <!-- 朝向 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">朝向 <span class="text-danger">*</span></div>
            <DictSelect category="orientation" v-model="roomForm.orientation" placeholder="请选择朝向" title="选择朝向" />
            <div v-if="roomFormErrors.orientation" class="text-danger text-xs mt-1">{{ roomFormErrors.orientation }}</div>
          </div>

          <!-- 可入住时间 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">可入住时间</div>
            <input
              type="date"
              v-model="roomForm.available_date"
              class="w-full bg-gray-50 rounded-lg px-3 py-2.5 text-sm border-0 outline-none text-gray-900"
            />
          </div>

          <!-- 设施 -->
          <div>
            <div class="text-sm font-bold text-gray-900 mb-2">设施</div>
            <DictSelect category="facility" v-model="roomForm.facilities" multiple title="选择设施" placeholder="请选择设施" />
          </div>

          <!-- 租金方案 -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-bold text-gray-900">租金方案 <span class="text-danger">*</span></div>
              <span class="text-xs text-primary" @click="addRentalPlan">+ 添加方案</span>
            </div>
            <div v-if="roomForm.rental_plans.length === 0" class="text-sm text-gray-400 py-4 text-center">
              暂无租金方案，点击上方添加
            </div>
            <div v-if="roomFormErrors.rental_plans" class="text-danger text-xs mt-1">{{ roomFormErrors.rental_plans }}</div>
            <div v-else class="space-y-3">
              <div
                v-for="(plan, idx) in roomForm.rental_plans"
                :key="idx"
                class="bg-gray-50 rounded-lg p-3 space-y-2"
              >
                <div class="flex items-center justify-between">
                  <span class="text-sm font-bold text-gray-900">方案 {{ idx + 1 }}</span>
                  <van-icon name="delete-o" class="text-danger" @click="removeRentalPlan(idx)" />
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-600 w-16 flex-shrink-0">租期</span>
                  <div class="flex-1">
                    <DictSelect category="lease_term" v-model="plan.lease_term" title="选择租期" placeholder="请选择租期" />
                    <div v-if="rentalPlanErrors[idx]?.lease_term" class="text-danger text-xs mt-1">{{ rentalPlanErrors[idx].lease_term }}</div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-600 w-16 flex-shrink-0">月租金</span>
                  <div class="flex-1">
                    <van-field
                      v-model.number="plan.monthly_rent"
                      type="digit"
                      placeholder="请输入月租金（元）"
                      :border="false"
                      class="flex-1 bg-white rounded-lg"
                    />
                    <div v-if="rentalPlanErrors[idx]?.monthly_rent" class="text-danger text-xs mt-1">{{ rentalPlanErrors[idx].monthly_rent }}</div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-600 w-16 flex-shrink-0">支付方式</span>
                  <div class="flex-1">
                    <DictSelect category="payment_method" v-model="plan.payment_method" title="选择支付方式" placeholder="请选择支付方式" />
                    <div v-if="rentalPlanErrors[idx]?.payment_method" class="text-danger text-xs mt-1">{{ rentalPlanErrors[idx].payment_method }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 border-t border-gray-100 safe-area-bottom">
          <van-button type="primary" block round @click="saveRoom">
            {{ isEditingRoom ? '保存修改' : '确认添加' }}
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.edit-apartment-page {
  min-height: 100vh;
  background-color: $bg-color;
}

.form-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0;
}

@media (min-width: 768px) {
  .form-container {
    padding: 16px 24px;
  }
}

.text-danger {
  color: $danger;
}

.text-primary {
  color: $primary;
}

.room-modal {
  :deep(.van-popup__content) {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
}

:deep(.van-field) {
  background-color: #f7f8fa;
  border-radius: 8px;
  padding: 8px 12px;
}

:deep(.van-field__word-limit) {
  color: #969799;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
