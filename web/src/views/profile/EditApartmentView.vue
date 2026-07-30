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
  openAddRoom,
  openEditRoom,
  closeRoomModal,
  triggerRoomImageUpload,
  onRoomImageChange,
  removeRoomImage,
  addRentalPlan,
  removeRentalPlan,
  saveRoom,
  removeRoomType,
  canSubmit,
  validateForm,
  buildPayload,
} = useApartmentForm()

// Edit 页面使用 computed 绑定级联选择器（districtModel 替代 districtValue）
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

// ================= 加载房源详情 =================
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
    form.room_types = (data.room_types || []).map((r: RoomType) => ({
      id: r.id,
      name: r.name,
      images: [...r.images],
      facilities: [...r.facilities],
      layout_type: r.layout_type,
      window_type: r.window_type,
      floor: r.floor,
      rental_plans: (r.rental_plans || []).map((p: RentalPlan) => ({
        lease_term: p.lease_term,
        monthly_rent: p.monthly_rent,
        payment_method: p.payment_method,
      })),
    }))
  } catch {
    // 错误已在 request 拦截器中 toast
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
    await updateApartment(apartmentId.value, buildPayload())
    showToast('保存成功')
    router.replace('/profile/my-apartments')
  } catch {
    // 错误已在 request 拦截器中 toast
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

// ================= 初始化 =================
onMounted(() => {
  loadApartmentDetail()
})
</script>

<template>
  <div class="edit-apartment-page">
    <!-- 顶部导航 -->
    <van-nav-bar title="编辑房源" left-arrow @click-left="router.back()" fixed placeholder />

    <!-- 加载中 -->
    <div v-if="loadingDetail" class="flex items-center justify-center py-20">
      <van-loading type="spinner" color="#1989fa" />
    </div>

    <!-- 表单内容 -->
    <div v-else class="p-4 space-y-4">
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

      <!-- 房型列表 -->
      <div class="bg-white rounded-xl p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="text-sm font-bold text-gray-900">房型 <span class="text-danger">*</span></div>
          <span class="text-xs text-gray-400">至少添加 1 组</span>
        </div>

        <!-- 已添加房型卡片 -->
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

        <!-- 添加房型按钮 -->
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

    <!-- 房型弹窗 -->
    <van-popup v-model:show="showRoomModal" position="bottom" round :style="{ height: '90%' }" class="room-modal">
      <div class="flex flex-col h-full">
        <!-- 弹窗头部 -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <span class="text-base font-bold">{{ isEditingRoom ? '编辑房型' : '添加房型' }}</span>
          <van-icon name="cross" class="text-gray-400 text-lg" @click="closeRoomModal" />
        </div>

        <!-- 弹窗内容 -->
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
              <span class="text-xs text-gray-400 font-normal">（最多 5 张）</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(img, idx) in roomForm.images"
                :key="idx"
                class="relative w-20 h-20 rounded-lg overflow-hidden"
              >
                <van-image :src="img" fit="cover" class="w-full h-full" />
                <div class="absolute top-1 right-1 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center" @click="removeRoomImage(idx)">
                  <van-icon name="cross" class="text-white text-xs" />
                </div>
              </div>
              <div
                v-if="roomForm.images.length < 5"
                class="w-20 h-20 bg-gray-50 rounded-lg flex flex-col items-center justify-center border border-dashed border-gray-300"
                @click="triggerRoomImageUpload"
              >
                <van-icon v-if="uploadingRoomImage" name="loading" class="text-primary animate-spin" />
                <template v-else>
                  <van-icon name="photograph" class="text-gray-400 text-lg" />
                  <span class="text-xs text-gray-400 mt-1">上传</span>
                </template>
                <span v-if="uploadingRoomImage" class="text-xs text-primary mt-1">上传中</span>
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

        <!-- 弹窗底部 -->
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
