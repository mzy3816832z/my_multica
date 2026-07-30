import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'

// Vant 样式
import 'vant/lib/index.css'

// Tailwind
import './styles/tailwind.css'

// 全局样式
import './styles/global.scss'

const app = createApp(App)

app.use(pinia)
app.use(router)

app.mount('#app')
