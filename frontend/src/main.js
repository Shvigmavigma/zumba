import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'
import { installChunkRecovery } from './chunkRecovery'
import { messages } from './messages'
import { pageMessages } from './i18n/pages'
import { uiMessages } from './i18n/ui'
import { mergeMessages } from './i18n/merge'
import { state } from './store'
import { installUi } from './ui/plugin'
import './styles.css'
import './design/index.css'

const i18n = createI18n({
  legacy: false,
  locale: state.locale,
  fallbackLocale: 'en',
  messages: mergeMessages(messages, uiMessages, pageMessages)
})

installChunkRecovery(router)

const app = createApp(App)
installUi(app)
app.use(router).use(i18n).mount('#app')
