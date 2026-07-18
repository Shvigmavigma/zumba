import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'
import { messages } from './messages'
import { state } from './store'
import './styles.css'

const i18n = createI18n({
  legacy: false,
  locale: state.locale,
  fallbackLocale: 'en',
  messages
})

createApp(App).use(router).use(i18n).mount('#app')
