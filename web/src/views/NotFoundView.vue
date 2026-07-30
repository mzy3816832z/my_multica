<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-screen px-6">
    <van-empty description="页面不存在" />
    <van-button type="primary" class="mt-6" @click="router.push('/apartments')">
      返回首页
    </van-button>
  </div>
</template>
