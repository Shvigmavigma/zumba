<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { api } from '../api'
import { state } from '../store'

const races = ref([])
const cursor = ref(new Date())
const selected = ref(new Date().toISOString().slice(0, 10))

const days = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const first = new Date(year, month, 1)
  const start = new Date(first)
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7))
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    return date
  })
})

const selectedRaces = computed(() => races.value.filter((race) => race.datetime_start.slice(0, 10) === selected.value))

function shiftMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

onMounted(async () => {
  races.value = await api('/races?limit=100')
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <h1>RaceCalendar</h1>
      <div class="toolbar">
        <button class="icon-button" @click="shiftMonth(-1)"><ChevronLeft :size="18" /></button>
        <strong>{{ cursor.toLocaleDateString(state.locale, { month: 'long', year: 'numeric' }) }}</strong>
        <button class="icon-button" @click="shiftMonth(1)"><ChevronRight :size="18" /></button>
      </div>
    </div>
    <div class="calendar-grid">
      <button
        v-for="day in days"
        :key="day.toISOString()"
        class="calendar-day"
        :class="{ active: day.toISOString().slice(0, 10) === selected }"
        @click="selected = day.toISOString().slice(0, 10)"
      >
        <strong>{{ day.getDate() }}</strong>
        <p v-for="race in races.filter((item) => item.datetime_start.slice(0, 10) === day.toISOString().slice(0, 10)).slice(0, 2)" :key="race.id" class="pill">{{ race.name }}</p>
      </button>
    </div>
    <section class="section">
      <h2>{{ new Date(selected).toLocaleDateString(state.locale) }}</h2>
      <div class="race-list">
        <article v-for="race in selectedRaces" :key="race.id" class="card race-item">
          <span>{{ race.name }} · {{ race.track }}</span>
          <RouterLink class="button" :to="`/races/${race.id}`">Open</RouterLink>
        </article>
      </div>
    </section>
  </section>
</template>
