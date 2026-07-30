<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { getDicts } from '@/api/dict'
import type { DictItem } from '@/types'

interface Props {
  category: string
  modelValue?: string | string[]
  multiple?: boolean
  placeholder?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  multiple: false,
  placeholder: '请选择',
  title: '请选择',
})

const emit = defineEmits<{
  'update:modelValue': [value: string | string[]]
}>()

const items = ref<DictItem[]>([])
const loading = ref(false)
const error = ref('')
const showPicker = ref(false)

const selectedLabel = ref('')

function findLabel(code: string) {
  return items.value.find(i => i.code === code)?.label || code
}

const MAX_DISPLAY_LABELS = 3

function updateLabel() {
  if (props.multiple) {
    const codes = (props.modelValue as string[]) || []
    if (codes.length === 0) {
      selectedLabel.value = ''
    } else {
      const displayCodes = codes.slice(0, MAX_DISPLAY_LABELS)
      const labels = displayCodes.map(c => findLabel(c)).join('、')
      if (codes.length > MAX_DISPLAY_LABELS) {
        selectedLabel.value = labels + '...+' + (codes.length - MAX_DISPLAY_LABELS)
      } else {
        selectedLabel.value = labels
      }
    }
  } else {
    const code = props.modelValue as string
    selectedLabel.value = code ? findLabel(code) : ''
  }
}

async function loadDicts() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDicts(props.category)
    items.value = res
    updateLabel()
  } catch {
    error.value = '加载选项失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.category, () => {
  loadDicts()
})

watch(() => props.modelValue, () => {
  updateLabel()
}, { deep: true })

onMounted(() => {
  loadDicts()
})

function onConfirm({ selectedOptions }: { selectedOptions: { text: string; value: string }[] }) {
  if (props.multiple) {
    showToast('多项选择请使用多选模式')
    return
  }
  const selected = selectedOptions[0]
  if (selected) {
    emit('update:modelValue', selected.value)
  }
  showPicker.value = false
}

function onMultiConfirm() {
  emit('update:modelValue', [...tempSelected.value])
  showMultiPicker.value = false
}

function toggleItem(code: string) {
  const idx = tempSelected.value.indexOf(code)
  if (idx >= 0) {
    tempSelected.value.splice(idx, 1)
  } else {
    tempSelected.value.push(code)
  }
}

const showMultiPicker = ref(false)
const tempSelected = ref<string[]>([])

function openPicker() {
  if (props.multiple) {
    tempSelected.value = [...((props.modelValue as string[]) || [])]
    showMultiPicker.value = true
  } else {
    showPicker.value = true
  }
}

const columns = computed(() =>
  items.value.map(i => ({ text: i.label, value: i.code }))
)
</script>

<template>
  <div class="dict-select">
    <van-field
      v-model="selectedLabel"
      readonly
      clickable
      :placeholder="loading ? '加载中...' : placeholder"
      :border="false"
      class="bg-gray-50 rounded-lg"
      @click="openPicker"
    >
      <template #right-icon>
        <van-loading v-if="loading" size="16" />
      </template>
    </van-field>

    <div v-if="error" class="text-xs text-danger mt-1 px-3">
      {{ error }}
      <span class="text-primary ml-2" @click="loadDicts">重试</span>
    </div>
    <div v-else-if="!loading && items.length === 0" class="text-xs text-gray-400 mt-1 px-3">
      暂无选项数据
    </div>

    <van-popup v-model:show="showPicker" position="bottom" round>
      <van-picker
        :columns="columns"
        :title="title"
        @confirm="onConfirm"
        @cancel="showPicker = false"
      />
    </van-popup>

    <van-popup v-model:show="showMultiPicker" position="bottom" round :style="{ height: '60%', display: 'flex', flexDirection: 'column' }">
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0">
        <span class="text-base font-bold">{{ title }}</span>
        <span class="text-sm text-primary" @click="onMultiConfirm">确定</span>
      </div>
      <div class="flex-1 overflow-y-auto p-3">
        <van-checkbox-group :model-value="tempSelected">
          <van-cell-group :border="false">
            <van-cell
              v-for="item in items"
              :key="item.code"
              :title="item.label"
              clickable
              @click="toggleItem(item.code)"
            >
              <template #right-icon>
                <van-checkbox
                  :name="item.code"
                  :model-value="tempSelected.includes(item.code)"
                />
              </template>
            </van-cell>
          </van-cell-group>
        </van-checkbox-group>
      </div>
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.dict-select {
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
