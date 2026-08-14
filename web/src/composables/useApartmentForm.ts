import { ref, reactive, computed, watch, onMounted } from 'vue'
import { uploadImage } from '@/api/upload'
import { geocodeAddress } from '@/api/apartment'
import { useDistrictStore } from '@/stores/district'

export interface RoomTypeFormItem {
  id?: number
  name: string
  images: string[]
  facilities: string[]
  layout_type: string
  window_type: string
  floor: number | undefined
  area: number | undefined
  available_date: string
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
  longitude: number | null
  latitude: number | null
  contact_phone: string
  property_fee: number | undefined
  water_fee: string
  electric_fee: string
  service_fee: number | undefined
  other_fees: string
  room_types: RoomTypeFormItem[]
}

const DRAFT_KEY = 'publish_draft'
const COMPRESS_MAX_LONG_SIDE = 2000
const DRAFT_DEBOUNCE_MS = 30000

function compressImage(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        let { width, height } = img
        const longSide = Math.max(width, height)
        if (longSide <= COMPRESS_MAX_LONG_SIDE) {
          resolve(file)
          return
        }
        const ratio = COMPRESS_MAX_LONG_SIDE / longSide
        width = Math.round(width * ratio)
        height = Math.round(height * ratio)
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          resolve(file)
          return
        }
        ctx.drawImage(img, 0, 0, width, height)
        const mimeType = file.type === 'image/png' ? 'image/jpeg' : 'image/webp'
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob)
            } else {
              resolve(file)
            }
          },
          mimeType,
          0.85,
        )
      }
      img.onerror = () => resolve(file)
      img.src = reader.result as string
    }
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}

export function useApartmentForm() {
  const form = reactive<ApartmentForm>({
    name: '',
    cover_image: '',
    description: '',
    district_id: undefined,
    street_id: undefined,
    detail_address: '',
    longitude: null,
    latitude: null,
    contact_phone: '',
    property_fee: undefined,
    water_fee: '',
    electric_fee: '',
    service_fee: undefined,
    other_fees: '',
    room_types: [],
  })

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

  watch(() => form.name, () => { delete formErrors.name })
  watch(() => form.cover_image, () => { delete formErrors.cover_image })
  watch(() => form.description, () => { delete formErrors.description })
  watch(() => form.district_id, () => { delete formErrors.district_id })
  watch(() => form.street_id, () => { delete formErrors.street_id })
  watch(() => form.detail_address, () => { delete formErrors.detail_address })
  watch(() => form.contact_phone, () => { delete formErrors.contact_phone })
  watch(() => form.room_types.length, () => { if (form.room_types.length > 0) delete formErrors.room_types })

  const districtValue = ref<{ district_id?: number; street_id?: number }>({
    district_id: form.district_id,
    street_id: form.street_id,
  })

  watch(districtValue, (val) => {
    form.district_id = val.district_id
    form.street_id = val.street_id
  }, { deep: true })

  // ================= 房源定位 =================
  type LocationStatus = 'idle' | 'locating' | 'located' | 'failed'

  const districtStore = useDistrictStore()
  const locationStatus = ref<LocationStatus>('idle')

  function setLocation(lng: number | null, lat: number | null) {
    form.longitude = lng
    form.latitude = lat
    locationStatus.value = lng != null && lat != null ? 'located' : 'idle'
  }

  async function geocodeLocation() {
    if (form.district_id == null || form.street_id == null) {
      showToast('请先选择行政区与街道')
      return
    }
    if (!form.detail_address.trim()) {
      showToast('请先填写详细门牌号')
      return
    }

    if (!districtStore.loaded) {
      try {
        await districtStore.loadDistricts()
      } catch {
      }
    }

    const districtName = districtStore.getDistrictName(form.district_id)
    const streetName = districtStore.getStreetName(form.street_id)
    if (districtName === '-' || streetName === '-') {
      locationStatus.value = 'failed'
      showToast('定位失败，可在地图上手动点选')
      return
    }

    const address = `上海市${districtName}${streetName}${form.detail_address.trim()}`
    locationStatus.value = 'locating'
    try {
      const res = await geocodeAddress(address)
      const lng = Number(res.longitude)
      const lat = Number(res.latitude)
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        locationStatus.value = 'failed'
        showToast('定位失败，可在地图上手动点选')
        return
      }
      form.longitude = lng
      form.latitude = lat
      locationStatus.value = 'located'
      showToast('定位成功')
    } catch {
      locationStatus.value = 'failed'
      showToast('定位失败，可在地图上手动点选')
    }
  }

  let geocodeTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    () => [form.district_id, form.street_id, form.detail_address] as const,
    ([districtId, streetId, address]) => {
      if (districtId == null || streetId == null || !(address || '').trim()) return
      if (locationStatus.value === 'located' || locationStatus.value === 'locating') return
      if (geocodeTimer) clearTimeout(geocodeTimer)
      geocodeTimer = setTimeout(() => {
        geocodeLocation()
      }, 800)
    },
  )

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
      const compressed = await compressImage(file)
      const res = await uploadImage(new File([compressed], file.name, { type: compressed.type || file.type }))
      form.cover_image = res.url
      showToast('上传成功')
    } catch {
    } finally {
      uploadingCover.value = false
      target.value = ''
    }
  }

  function removeCover() {
    form.cover_image = ''
  }

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
    area: undefined,
    available_date: '',
    rental_plans: [],
  })

  watch(() => roomForm.name, () => { delete roomFormErrors.name })
  watch(() => roomForm.images.length, () => { if (roomForm.images.length > 0) delete roomFormErrors.images })
  watch(() => roomForm.layout_type, () => { delete roomFormErrors.layout_type })
  watch(() => roomForm.window_type, () => { delete roomFormErrors.window_type })
  watch(() => roomForm.floor, () => { delete roomFormErrors.floor })
  watch(() => roomForm.area, () => { delete roomFormErrors.area })
  watch(() => roomForm.rental_plans.length, () => { if (roomForm.rental_plans.length > 0) delete roomFormErrors.rental_plans })

  const roomImageUploader = ref<HTMLInputElement | null>(null)
  const uploadingRoomImage = ref(false)

  interface PendingRoomImage {
    file: File
    status: 'uploading' | 'failed'
    error?: string
  }

  const pendingRoomImages = ref<PendingRoomImage[]>([])

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
      area: room.area,
      available_date: room.available_date || '',
      rental_plans: room.rental_plans.map(p => ({ ...p })),
    })
    pendingRoomImages.value = []
    showRoomModal.value = true
  }

  function resetRoomForm() {
    roomForm.name = ''
    roomForm.images = []
    roomForm.facilities = []
    roomForm.layout_type = ''
    roomForm.window_type = ''
    roomForm.floor = undefined
    roomForm.area = undefined
    roomForm.available_date = ''
    roomForm.rental_plans = []
    pendingRoomImages.value = []
    Object.keys(roomFormErrors).forEach(k => delete roomFormErrors[k])
    rentalPlanErrors.value = {}
  }

  function closeRoomModal() {
    showRoomModal.value = false
  }

  function triggerRoomImageUpload() {
    if (roomForm.images.length + pendingRoomImages.value.length >= 5) {
      showToast('最多上传 5 张图片')
      return
    }
    roomImageUploader.value?.click()
  }

  async function uploadSingleRoomImage(file: File) {
    const compressed = await compressImage(file)
    const res = await uploadImage(new File([compressed], file.name, { type: compressed.type || file.type }))
    roomForm.images.push(res.url)
  }

  async function onRoomImageChange(e: Event) {
    const target = e.target as HTMLInputElement
    const files = Array.from(target.files || [])
    if (files.length === 0) return

    const remainingSlots = 5 - roomForm.images.length - pendingRoomImages.value.length
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

    for (const file of validFiles) {
      const pending: PendingRoomImage = { file, status: 'uploading' }
      pendingRoomImages.value.push(pending)
    }

    uploadingRoomImage.value = true
    for (const pending of pendingRoomImages.value) {
      try {
        await uploadSingleRoomImage(pending.file)
        pendingRoomImages.value = pendingRoomImages.value.filter(p => p !== pending)
      } catch {
        pending.status = 'failed'
        pending.error = '上传失败'
      }
    }
    uploadingRoomImage.value = false

    const failedCount = pendingRoomImages.value.filter(p => p.status === 'failed').length
    const successCount = validFiles.length - failedCount
    if (successCount > 0 && failedCount > 0) {
      showToast(`${successCount} 张上传成功，${failedCount} 张失败`)
    } else if (failedCount > 0) {
      showToast(`全部 ${failedCount} 张上传失败`)
    }

    target.value = ''
  }

  async function retryRoomImage(pending: PendingRoomImage) {
    pending.status = 'uploading'
    pending.error = undefined
    try {
      await uploadSingleRoomImage(pending.file)
      pendingRoomImages.value = pendingRoomImages.value.filter(p => p !== pending)
    } catch {
      pending.status = 'failed'
      pending.error = '上传失败'
    }
  }

  function removePendingRoomImage(index: number) {
    pendingRoomImages.value.splice(index, 1)
  }

  function removeRoomImage(index: number) {
    roomForm.images.splice(index, 1)
  }

  const dragIndex = ref(-1)
  const dragOverIndex = ref(-1)

  function onDragStart(index: number) {
    dragIndex.value = index
  }

  function onDragOver(index: number) {
    dragOverIndex.value = index
  }

  function onDrop(index: number) {
    if (dragIndex.value < 0 || dragIndex.value === index) {
      dragIndex.value = -1
      dragOverIndex.value = -1
      return
    }
    const images = [...roomForm.images]
    const [moved] = images.splice(dragIndex.value, 1)
    images.splice(index, 0, moved)
    roomForm.images = images
    dragIndex.value = -1
    dragOverIndex.value = -1
  }

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
    if (roomForm.area === undefined || roomForm.area === null) {
      roomFormErrors.area = '请输入房型面积'
      hasError = true
    } else if (roomForm.area < 0.5 || roomForm.area > 500) {
      roomFormErrors.area = '面积范围 0.5-500 ㎡'
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
      area: roomForm.area !== undefined && roomForm.area !== null ? Number(roomForm.area) : undefined,
      available_date: roomForm.available_date || '',
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

  async function removeRoomType(index: number) {
    try {
      await showConfirmDialog({
        title: '确认删除',
        message: '确定要删除该房型吗？',
      })
      form.room_types.splice(index, 1)
      showToast('已删除')
    } catch {
    }
  }

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
    if (form.other_fees.trim().length > 100) {
      formErrors.other_fees = '其他费用不能超过 100 字'
      hasError = true
    }

    return !hasError
  }

  function buildPayload() {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      cover_image: form.cover_image,
      description: form.description.trim(),
      district_id: form.district_id as number,
      street_id: form.street_id as number,
      detail_address: form.detail_address.trim(),
      longitude: form.longitude,
      latitude: form.latitude,
      contact_phone: form.contact_phone.trim(),
      property_fee: form.property_fee !== undefined && form.property_fee !== null ? Number(form.property_fee) : undefined,
      water_fee: form.water_fee || undefined,
      electric_fee: form.electric_fee || undefined,
      service_fee: form.service_fee !== undefined && form.service_fee !== null ? Number(form.service_fee) : undefined,
      other_fees: form.other_fees.trim() || undefined,
      room_types: form.room_types.map(r => ({
        name: r.name,
        images: r.images,
        facilities: r.facilities,
        layout_type: r.layout_type,
        window_type: r.window_type,
        floor: r.floor as number,
        area: r.area !== undefined && r.area !== null ? Number(r.area) : undefined,
        available_date: r.available_date || undefined,
        rental_plans: r.rental_plans.map(p => ({
          lease_term: p.lease_term,
          monthly_rent: p.monthly_rent as number,
          payment_method: p.payment_method,
        })),
      })),
    }
    return payload
  }

  // ================= 草稿 =================
  const draftLoaded = ref(false)
  const showDraftDialog = ref(false)

  function saveDraft() {
    try {
      const draftData = JSON.parse(JSON.stringify(form))
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draftData))
    } catch {
    }
  }

  let draftTimer: ReturnType<typeof setTimeout> | null = null

  watch(form, () => {
    if (draftTimer) clearTimeout(draftTimer)
    draftTimer = setTimeout(saveDraft, DRAFT_DEBOUNCE_MS)
  }, { deep: true })

  function checkDraft() {
    if (draftLoaded.value) return
    draftLoaded.value = true
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (raw) {
        const draft = JSON.parse(raw) as ApartmentForm
        if (draft.name || draft.cover_image || draft.description || draft.room_types.length > 0) {
          showDraftDialog.value = true
        }
      }
    } catch {
    }
  }

  function restoreDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (raw) {
        const draft = JSON.parse(raw) as ApartmentForm
        Object.assign(form, {
          name: draft.name || '',
          cover_image: draft.cover_image || '',
          description: draft.description || '',
          district_id: draft.district_id ?? undefined,
          street_id: draft.street_id ?? undefined,
          detail_address: draft.detail_address || '',
          longitude: draft.longitude ?? null,
          latitude: draft.latitude ?? null,
          contact_phone: draft.contact_phone || '',
          property_fee: draft.property_fee ?? undefined,
          water_fee: draft.water_fee || '',
          electric_fee: draft.electric_fee || '',
          service_fee: draft.service_fee ?? undefined,
          other_fees: draft.other_fees || '',
          room_types: draft.room_types || [],
        })
        if (draft.district_id !== undefined) {
          districtValue.value = {
            district_id: draft.district_id,
            street_id: draft.street_id,
          }
        }
        locationStatus.value =
          form.longitude != null && form.latitude != null ? 'located' : 'idle'
      }
    } catch {
    }
    showDraftDialog.value = false
  }

  function discardDraft() {
    clearDraft()
    showDraftDialog.value = false
  }

  function clearDraft() {
    localStorage.removeItem(DRAFT_KEY)
  }

  // ================= 返回 =================
  return {
    form,
    formErrors,
    roomFormErrors,
    rentalPlanErrors,
    clearRentalPlanError,
    districtValue,
    locationStatus,
    setLocation,
    geocodeLocation,
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
    pendingRoomImages,
    openAddRoom,
    openEditRoom,
    resetRoomForm,
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
    showDraftDialog,
    checkDraft,
    restoreDraft,
    discardDraft,
    clearDraft,
  }
}
