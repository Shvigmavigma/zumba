<script setup>
// Digits roll vertically to their new value, like an iOS clock or a pit board
// (motion-primitives' SlidingNumber idea, done with CSS transforms).
import { computed } from 'vue'

const props = defineProps({
  value: { type: [String, Number], required: true }
})

const chars = computed(() => String(props.value).split('').map((char, index, list) => ({
  key: list.length - index,
  char,
  digit: /\d/.test(char) ? Number(char) : null
})))
</script>

<template>
  <span class="rolling ui-num" :aria-label="String(value)">
    <span v-for="item in chars" :key="item.key" class="rolling__cell" aria-hidden="true">
      <span v-if="item.digit !== null" class="rolling__strip" :style="{ transform: `translateY(${item.digit * -10}%)` }">
        <span v-for="n in 10" :key="n">{{ n - 1 }}</span>
      </span>
      <span v-else>{{ item.char }}</span>
    </span>
  </span>
</template>

<style scoped>
.rolling {
  display: inline-flex;
  line-height: 1;
}

.rolling__cell {
  position: relative;
  display: inline-block;
  height: 1em;
  overflow: hidden;
}

.rolling__strip {
  display: flex;
  flex-direction: column;
  transition: transform 700ms var(--ease-ios);
}

.rolling__strip > span {
  height: 1em;
}

@media (prefers-reduced-motion: reduce) {
  .rolling__strip {
    transition: none;
  }
}
</style>
