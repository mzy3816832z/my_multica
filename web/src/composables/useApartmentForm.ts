import { ref, reactive, computed, watch } from 'vue'
import { uploadImage } from '@/api/upload'

export interface RoomTypeFormItem {
  id?: number
  name: string
  images: string[]
  facilities: string[]
  layout_type: string
  window_type: string
  floor: number | undefined
  rental_plans: RentalPlanFormItem[]
}

export interface RentalPlanFormItem {
  lease_term: string
  monthly_rent: number | undefined
  payment_method: string
}

export interface ApartmentForm {
  name: string
  cover_image: string
  description: string
  district_id: number | undefined
  street_id: number | undefined
  detail_address: string
  contact_phone: string
  room_types: RoomTypeFormItem[]
}

export function useApartmentForm() {
  // ================= 表单数据 =================
  const form = reactive<ApartmentForm>({
    name: '',
    cover_image: '',
    description: '',
    district_id: undefined,
    street_id: undefined,
    detail_address: '',
    contact_phone: '',
    room_types: [],
  })

  // ================= 表单校验错误 =================
  const formErrors = reactive<Record<string, string>>({})
  const roomFormErrors = reactive<Record<string, string>>({})
  const rentalPlanErrors = ref<Record<number, Record<string, string>>>({})

  function clearRentalPlanError(planIdx: number, field: string) {
    if (rentalPlanErrors.value[planIdx]) {
      delete rentalPlanErrors.value[planIdx][field]
      if (Object.keys(rentalPlanErrors.value[planIdx]).length === 0) {
        delete rentalPlanErrors.value[planIdx]
      }
    }
  }

  // 主表单字段变更时清除对应错误
  watch(() => form.name, () => { delete formErrors.name })
  watch(() => form.cover_image, () => { delete formErrors.cover_image })
  watch(() => form.description, () => { delete formErrors.description })
  watch(() => form.district_id, () => { delete formErrors.district_id })
  watch(() => form.street_id, () => { delete formErrors.street_id })
  watch(() => form.detail_address, () => { delete formErrors.detail_address })
  watch(() => form.contact_phone, () => { delete formErrors.contact_phone })
  watch(() => form.room_types.length, () => { if (form.room_types.length > 0) delete formErrors.room_types })

  // ================= 行政区级联值绑定 =================
  const districtValue = ref<{ district_id?: number; street_id?: number }>({
    district_id: form.district_id,
    street_id: form.street_id,
  })

  watch(districtValue, (val) => {
    form.district_id = val.district_id
    form.street_id = val.street_id
  }, { deep: true })

  // ================= 图片上传 =================
  const coverUploader = ref<HTMLInputElement | null>(null)
  const uploadingCover = ref(false)

  function triggerCoverUpload() {
    coverUploader.value?.click()
  }

  async function onCoverChange(e: Event) {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (!file) return

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      showToast('仅支持 jpg/png/webp 格式')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast('图片大小不能超过 5MB')
      return
    }

    uploadingCover.value = true
    try {
      const res = await uploadImage(file)
      form.cover_image = res.url
      showToast('上传成功')
    } catch {
      // 错误已在 request 拦截器中 toast
    } finally {
      uploadingCover.value = false
      target.value = ''
    }
  }

  function removeCover() {
    form.cover_image = ''
  }

  // ================= 房型弹窗 =================
  const showRoomModal = ref(false)
  const isEditingRoom = ref(false)
  const editingRoomIndex = ref(-1)

  const roomForm = reactive<RoomTypeFormItem>({
    name: '',
    images: [],
    facilities: [],
    layout_type: '',
    window_type: '',
    floor: undefined,
    rental_plans: [],
  })

  // 房型表单字段变更时清除对应错误
  watch(() => roomForm.name, () => { delete roomFormErrors.name })
  watch(() => roomForm.images.length, () => { if (roomForm.images.length > 0) delete roomFormErrors.images })
  watch(() => roomForm.layout_type, () => { delete roomFormErrors.layout_type })
  watch(() => roomForm.window_type, () => { delete roomFormErrors.window_type })
  watch(() => roomForm.floor, () => { delete roomFormErrors.floor })
  watch(() => roomForm.rental_plans.length, () => { if (roomForm.rental_plans.length > 0) delete roomFormErrors.rental_plans })

  const roomImageUploader = ref<HTMLInputElement | null>(null)
  const uploadingRoomImage = ref(false)

  function openAddRoom() {
    isEditingRoom.value = false
    editingRoomIndex.value = -1
    resetRoomForm()
    showRoomModal.value = true
  }

  function openEditRoom(index: number) {
    isEditingRoom.value = true
    editingRoomIndex.value = index
    const room = form.room_types[index]
    Object.assign(roomForm, {
      name: room.name,
      images: [...room.images],
      facilities: [...room.facilities],
      layout_type: room.layout_type,
      window_type: room.window_type,
      floor: room.floor,
      rental_plans: room.rental_plans.map(p => ({ ...p })),
    })
    showRoomModal.value = true
  }

  function resetRoomForm() {
    roomForm.name = ''
    roomForm.images = []
    roomForm.facilities = []
    roomForm.layout_type = ''
    roomForm.window_type = ''
    roomForm.floor = undefined
    roomForm.rental_plans = []
    Object.keys(roomFormErrors).forEach(k => delete roomFormErrors[k])
    rentalPlanErrors.value = {}
  }

  function closeRoomModal() {
    showRoomModal.value = false
  }

  // 房型图片上传
  function triggerRoomImageUpload() {
    if (roomForm.images.length >= 5) {
      showToast('最多上传 5 张图片')
      return
    }
    roomImageUploader.value?.click()
  }

  async function onRoomImageChange(e: Event) {
    const target = e.target as HTMLInputElement
    const files = Array.from(target.files || [])
    if (files.length === 0) return

    const remainingSlots = 5 - roomForm.images.length
    if (files.length > remainingSlots) {
      showToast(`最多上传 5 张图片，当前还可上传 ${remainingSlots} 张`)
      target.value = ''
      return
    }

    const validFiles = files.filter(file => {
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        showToast(`${file.name} 格式不支持，已跳过`)
        return false
      }
      if (file.size > 5 * 1024 * 1024) {
        showToast(`${file.name} 超过 5MB，已跳过`)
        return false
      }
      return true
    }).slice(0, remainingSlots)

    if (validFiles.length === 0) {
      target.value = ''
      return
    }

    uploadingRoomImage.value = true
    let successCount = 0
    try {
      for (const file of validFiles) {
        try {
          const res = await uploadImage(file)
          roomForm.images.push(res.url)
          successCount++
        } catch {
          showToast(`${file.name} 上传失败`)
        }
      }
      if (successCount > 0) {
        showToast(successCount === validFiles.length
          ? `成功上传 ${successCount} 张图片`
          : `${successCount} 张上传成功，${validFiles.length - successCount} 张失败`)
      }
    } catch {
      // 错误已在 request 拦截器中 toast
    } finally {
      uploadingRoomImage.value = false
      target.value = ''
    }
  }

  function removeRoomImage(index: number) {
    roomForm.images.splice(index, 1)
  }

  // 租金方案
  function addRentalPlan() {
    roomForm.rental_plans.push({
      lease_term: '',
      monthly_rent: undefined,
      payment_method: '',
    })
  }

  function removeRentalPlan(index: number) {
    roomForm.rental_plans.splice(index, 1)
  }

  // 保存房型
  function saveRoom() {
    Object.keys(roomFormErrors).forEach(k => delete roomFormErrors[k])
    rentalPlanErrors.value = {}
    let hasError = false

    if (!roomForm.name.trim()) {
      roomFormErrors.name = '请输入房型名称'
      hasError = true
    }
    if (roomForm.images.length === 0) {
      roomFormErrors.images = '请至少上传 1 张房型图片'
      hasError = true
    }
    if (!roomForm.layout_type) {
      roomFormErrors.layout_type = '请选择户型'
      hasError = true
    }
    if (!roomForm.window_type) {
      roomFormErrors.window_type = '请选择窗户类型'
      hasError = true
    }
    if (roomForm.floor === undefined || roomForm.floor === null) {
      roomFormErrors.floor = '请输入楼层'
      hasError = true
    }
    if (roomForm.rental_plans.length === 0) {
      roomFormErrors.rental_plans = '请至少添加 1 组租金方案'
      hasError = true
    }
    for (let i = 0; i < roomForm.rental_plans.length; i++) {
      const plan = roomForm.rental_plans[i]
      if (!plan.lease_term) {
        if (!rentalPlanErrors.value[i]) rentalPlanErrors.value[i] = {}
        rentalPlanErrors.value[i].lease_term = '请选择租期'
        hasError = true
      }
      if (!plan.monthly_rent || plan.monthly_rent <= 0) {
        if (!rentalPlanErrors.value[i]) rentalPlanErrors.value[i] = {}
        rentalPlanErrors.value[i].monthly_rent = '请输入有效的月租金'
        hasError = true
      }
      if (!plan.payment_method) {
        if (!rentalPlanErrors.value[i]) rentalPlanErrors.value[i] = {}
        rentalPlanErrors.value[i].payment_method = '请选择支付方式'
        hasError = true
      }
    }

    if (hasError) {
      showToast('请完善房型信息')
      return
    }

    const roomData: RoomTypeFormItem = {
      name: roomForm.name.trim(),
      images: [...roomForm.images],
      facilities: [...roomForm.facilities],
      layout_type: roomForm.layout_type,
      window_type: roomForm.window_type,
      floor: Number(roomForm.floor),
      rental_plans: roomForm.rental_plans.map(p => ({
        lease_term: p.lease_term,
        monthly_rent: Number(p.monthly_rent),
        payment_method: p.payment_method,
      })),
    }

    if (isEditingRoom.value && editingRoomIndex.value >= 0) {
      form.room_types[editingRoomIndex.value] = roomData
    } else {
      form.room_types.push(roomData)
    }

    showToast(isEditingRoom.value ? '房型已更新' : '房型已添加')
    closeRoomModal()
  }

  // 删除房型
  async function removeRoomType(index: number) {
    try {
      await showConfirmDialog({
        title: '确认删除',
        message: '确定要删除该房型吗？',
      })
      form.room_types.splice(index, 1)
      showToast('已删除')
    } catch {
      // 取消删除
    }
  }

  // ================= 表单校验与提交 =================
  const canSubmit = computed(() => {
    return (
      form.name.trim() &&
      form.cover_image &&
      form.description.trim() &&
      form.district_id !== undefined &&
      form.street_id !== undefined &&
      form.detail_address.trim() &&
      form.contact_phone.trim() &&
      form.room_types.length > 0
    )
  })

  function validateForm(): boolean {
    Object.keys(formErrors).forEach(k => delete formErrors[k])
    let hasError = false

    if (!form.name.trim()) {
      formErrors.name = '请输入公寓名称'
      hasError = true
    } else if (form.name.trim().length > 50) {
      formErrors.name = '公寓名称不能超过 50 字'
      hasError = true
    }
    if (!form.cover_image) {
      formErrors.cover_image = '请上传公寓总览图'
      hasError = true
    }
    if (!form.description.trim()) {
      formErrors.description = '请输入公寓描述'
      hasError = true
    } else if (form.description.trim().length > 500) {
      formErrors.description = '公寓描述不能超过 500 字'
      hasError = true
    }
    if (form.district_id === undefined) {
      formErrors.district_id = '请选择行政区'
      hasError = true
    }
    if (form.street_id === undefined) {
      formErrors.street_id = '请选择街道/镇'
      hasError = true
    }
    if (!form.detail_address.trim()) {
      formErrors.detail_address = '请输入详细门牌号'
      hasError = true
    }
    if (!form.contact_phone.trim()) {
      formErrors.contact_phone = '请输入联系电话'
      hasError = true
    } else if (!/^1[3-9]\d{9}$/.test(form.contact_phone.trim())) {
      formErrors.contact_phone = '请输入正确的手机号码'
      hasError = true
    }
    if (form.room_types.length === 0) {
      formErrors.room_types = '请至少添加 1 组房型'
      hasError = true
    }

    return !hasError
  }

  function buildPayload() {
    return {
      name: form.name.trim(),
      cover_image: form.cover_image,
      description: form.description.trim(),
      district_id: form.district_id as number,
      street_id: form.street_id as number,
      detail_address: form.detail_address.trim(),
      contact_phone: form.contact_phone.trim(),
      room_types: form.room_types.map(r => ({
        name: r.name,
        images: r.images,
        facilities: r.facilities,
        layout_type: r.layout_type,
        window_type: r.window_type,
        floor: r.floor as number,
        rental_plans: r.rental_plans.map(p => ({
          lease_term: p.lease_term,
          monthly_rent: p.monthly_rent as number,
          payment_method: p.payment_method,
        })),
      })),
    }
  }

  return {
    form,
    formErrors,
    roomFormErrors,
    rentalPlanErrors,
    clearRentalPlanError,
    districtValue,
    coverUploader,
    uploadingCover,
    triggerCoverUpload,
    onCoverChange,
    removeCover,
    showRoomModal,
    isEditingRoom,
    editingRoomIndex,
    roomForm,
    roomImageUploader,
    uploadingRoomImage,
    openAddRoom,
    openEditRoom,
    resetRoomForm,
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
  }
}
