<script setup lang="ts">
import { ref, watch, onMounted, nextTick, computed } from 'vue'
import { getDistricts } from '@/api/dict'
import type { District } from '@/types'

const modelValue = defineModel<{ district_id?: number; street_id?: number }>({
  default: () => ({})
})

const districts = ref<District[]>([])
const streets = ref<District[]>([])
const loadingDistricts = ref(false)
const loadingStreets = ref(false)
const errorDistricts = ref('')
const errorStreets = ref('')

const selectedDistrictId = ref<number | undefined>(modelValue.value.district_id)
const selectedStreetId = ref<number | undefined>(modelValue.value.street_id)

const districtLabel = ref('请选择行政区')
const streetLabel = ref('请选择街道/镇')

const showDistrictPicker = ref(false)
const showStreetPicker = ref(false)

async function loadDistricts() {
  loadingDistricts.value = true
  errorDistricts.value = ''
  try {
    const res = await getDistricts({ level: 1 })
    districts.value = res
  } catch {
    errorDistricts.value = '加载行政区失败'
  } finally {
    loadingDistricts.value = false
  }
}

async function loadStreets(parentId: number) {
  loadingStreets.value = true
  errorStreets.value = ''
  streets.value = []
  try {
    const res = await getDistricts({ level: 2, parent_id: parentId })
    streets.value = res
  } catch {
    errorStreets.value = '加载街道失败'
  } finally {
    loadingStreets.value = false
  }
}

function onDistrictConfirm({ selectedOptions }: { selectedOptions: { text: string; value: number }[] }) {
  const district = selectedOptions[0]
  if (district) {
    selectedDistrictId.value = district.value
    districtLabel.value = district.text
    selectedStreetId.value = undefined
    streetLabel.value = '请选择街道/镇'
    loadStreets(district.value)
    emitUpdate()
  }
  showDistrictPicker.value = false
}

function onStreetConfirm({ selectedOptions }: { selectedOptions: { text: string; value: number }[] }) {
  const street = selectedOptions[0]
  if (street) {
    selectedStreetId.value = street.value
    streetLabel.value = street.text
    emitUpdate()
  }
  showStreetPicker.value = false
}

function emitUpdate() {
  isUpdatingInternally.value = true
  modelValue.value = {
    district_id: selectedDistrictId.value,
    street_id: selectedStreetId.value
  }
  nextTick(() => {
    isUpdatingInternally.value = false
  })
}

const isUpdatingInternally = ref(false)

watch(() => modelValue.value, (val) => {
  if (isUpdatingInternally.value) return

  const dId = val?.district_id
  const sId = val?.street_id

  if (dId !== selectedDistrictId.value) {
    selectedDistrictId.value = dId
    selectedStreetId.value = undefined
    streetLabel.value = '请选择街道/镇'
    streets.value = []

    if (dId) {
      const found = districts.value.find(d => d.id === dId)
      if (found) {
        districtLabel.value = found.name
        loadStreets(dId).then(() => {
          if (sId) {
            selectedStreetId.value = sId
            const s = streets.value.find(s => s.id === sId)
            if (s) {
              streetLabel.value = s.name
            }
          }
        })
      }
    }
  } else if (sId !== selectedStreetId.value) {
    selectedStreetId.value = sId
    if (sId && streets.value.length > 0) {
      const found = streets.value.find(s => s.id === sId)
      if (found) {
        streetLabel.value = found.name
      }
    }
  }
}, { deep: true })

onMounted(() => {
  loadDistricts()

  const dId = modelValue.value.district_id
  const sId = modelValue.value.street_id
  if (dId) {
    selectedDistrictId.value = dId
    loadStreets(dId).then(() => {
      if (sId) {
        selectedStreetId.value = sId
        const found = streets.value.find(s => s.id === sId)
        if (found) {
          streetLabel.value = found.name
        }
      }
    })
  }
})

const districtColumns = computed(() =>
  districts.value.map(d => ({ text: d.name, value: d.id }))
)

const streetColumns = computed(() =>
  streets.value.map(s => ({ text: s.name, value: s.id }))
)
</script>

<template>
  <div class="district-cascader">
    <div class="flex gap-3">
      <van-field
        v-model="districtLabel"
        readonly
        clickable
        :placeholder="loadingDistricts ? '加载中...' : '请选择行政区'"
        :border="false"
        class="flex-1 bg-gray-50 rounded-lg"
        @click="showDistrictPicker = true"
      >
        <template #right-icon>
          <van-loading v-if="loadingDistricts" size="16" />
        </template>
      </van-field>

      <van-field
        v-model="streetLabel"
        readonly
        clickable
        :disabled="!selectedDistrictId || loadingStreets"
        :placeholder="loadingStreets ? '加载中...' : '请选择街道/镇'"
        :border="false"
        class="flex-1 bg-gray-50 rounded-lg"
        @click="selectedDistrictId ? showStreetPicker = true : undefined"
      >
        <template #right-icon>
          <van-loading v-if="loadingStreets" size="16" />
        </template>
      </van-field>
    </div>

    <div v-if="errorDistricts" class="text-xs text-danger mt-2 px-3">
      {{ errorDistricts }}
      <span class="text-primary ml-2" @click="loadDistricts">重试</span>
    </div>
    <div v-else-if="!loadingDistricts && districts.length === 0" class="text-xs text-gray-400 mt-2 px-3">
      暂无行政区数据
    </div>

    <div v-if="errorStreets" class="text-xs text-danger mt-1 px-3">
      {{ errorStreets }}
    </div>
    <div v-else-if="selectedDistrictId && !loadingStreets && streets.length === 0 && !errorStreets" class="text-xs text-gray-400 mt-1 px-3">
      暂无街道/镇数据
    </div>

    <van-popup v-model:show="showDistrictPicker" position="bottom" round>
      <van-picker
        :columns="districtColumns"
        title="选择行政区"
        @confirm="onDistrictConfirm"
        @cancel="showDistrictPicker = false"
      />
    </van-popup>

    <van-popup v-model:show="showStreetPicker" position="bottom" round>
      <van-picker
        :columns="streetColumns"
        title="选择街道/镇"
        @confirm="onStreetConfirm"
        @cancel="showStreetPicker = false"
      />
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.district-cascader {
  :deep(.van-field) {
    background-color: #f7f8fa;
    border-radius: 8px;
    padding: 8px 12px;
  }
}

.text-danger {
  color: $danger;
}

.text-primary {
  color: $primary;
}
</style>
