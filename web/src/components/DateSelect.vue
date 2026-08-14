<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  modelValue?: string
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '请选择日期',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const showCalendar = ref(false)

function startOfToday(): Date {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return now
}

const minDate = startOfToday()

function parseDate(value: string): Date | null {
  if (!value) return null
  const parts = value.split('-')
  if (parts.length !== 3) return null
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return isNaN(d.getTime()) ? null : d
}

const defaultDate = computed(() => parseDate(props.modelValue) ?? minDate)

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function onConfirm(date: Date) {
  emit('update:modelValue', formatDate(date))
  showCalendar.value = false
}

function onClear() {
  emit('update:modelValue', '')
}
</script>

<template>
  <div class="date-select">
    <van-field
      :model-value="modelValue"
      readonly
      clickable
      :placeholder="placeholder"
      :border="false"
      class="bg-gray-50 rounded-lg"
      @click="showCalendar = true"
    >
      <template #right-icon>
        <van-icon
          v-if="modelValue"
          name="clear"
          class="text-gray-400"
          @click.stop="onClear"
        />
      </template>
    </van-field>

    <van-calendar
      v-model:show="showCalendar"
      :min-date="minDate"
      :default-date="defaultDate"
      :allow-same-day="true"
      @confirm="onConfirm"
    />
  </div>
</template>

<style scoped lang="scss">
.date-select {
  :deep(.van-field) {
    background-color: #f7f8fa;
    border-radius: 8px;
    padding: 8px 12px;
  }
}
</style>
