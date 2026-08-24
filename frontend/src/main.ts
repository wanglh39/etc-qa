import { createApp } from 'vue'
import App from './App.vue'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/design-tokens.css'
// 引入中文语言包
import zhCn from 'element-plus/es/locale/lang/zh-cn'

// 2. 引入 Pinia 状态管理
import { createPinia } from 'pinia'
const pinia = createPinia()

// 3. 引入 Vue Router
import router from './router'

// 创建应用实例
const app = createApp(App)

// --- 插件注册区域 ---

// 先注册 Pinia (如果路由守卫依赖 store，必须在 router 之前)
app.use(pinia)

// 注册路由
app.use(router)

// 注册 UI 库并配置中文
app.use(ElementPlus, {
  locale: zhCn,
})

// 挂载应用
app.mount('#app')
