<script setup lang="ts">
const props = defineProps<{
  visible: boolean
  phone: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const actions = [
  { name: '拨打', color: '#1989fa' },
  { name: '复制', color: '#323233' },
]

function onSelect(action: { name: string }) {
  if (action.name === '拨打') {
    window.location.href = `tel:${props.phone}`
  } else if (action.name === '复制') {
    navigator.clipboard.writeText(props.phone).then(() => {
      showToast('已复制到剪贴板')
    }).catch(() => {
      showToast('复制失败')
    })
  }
  emit('update:visible', false)
}

function onCancel() {
  emit('update:visible', false)
}
</script>

<template>
  <van-action-sheet
    :show="visible"
    :actions="actions"
    :title="phone"
    cancel-text="取消"
    close-on-click-action
    @select="onSelect"
    @cancel="onCancel"
    @close="onCancel"
  />
</template>
