import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const loading = ref(false)
  const loadingText = ref('加载中...')

  function showLoading(text = '加载中...') {
    loading.value = true
    loadingText.value = text
  }

  function hideLoading() {
    loading.value = false
    loadingText.value = '加载中...'
  }

  return {
    loading,
    loadingText,
    showLoading,
    hideLoading,
  }
})
