<script setup>
// Pilot roles and stickers. A pilot can collect many, so the row stays
// compact: the first few show, a "+N" pill opens the rest in place, and the
// row wraps inside whatever card holds it instead of running past its edge.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { roleList } from '../pilotRoles'

const props = defineProps({
  /** A list of roles; a single role object is taken as a list of one (see pilotRoles.js). */
  roles: {
    type: [Array, Object],
    default: () => []
  },
  /** Roles visible while collapsed; the rest open on click. */
  limit: {
    type: Number,
    default: 2
  }
})

const { t } = useI18n()
const expanded = ref(false)
const list = computed(() => roleList(props.roles))
const hiddenCount = computed(() => Math.max(0, list.value.length - props.limit))
const visible = computed(() => (expanded.value || !hiddenCount.value ? list.value : list.value.slice(0, props.limit)))

function modeOf(role) {
  return role.display_mode || (role.image_url ? 'text_image' : 'text')
}
</script>

<template>
  <span v-if="list.length" class="pilot-roles" :class="{ 'is-expanded': expanded }" :aria-label="t('ui.roles.label')">
    <span
      v-for="(role, index) in visible"
      :key="role.id"
      class="pilot-role-badge"
      :class="[`is-${modeOf(role)}`, { 'is-extra': index >= limit }]"
      :style="{ '--pilot-role-border': role.border_color || 'var(--primary)' }"
      :title="role.name"
    >
      <span v-if="modeOf(role) !== 'image'" class="pilot-role-text">{{ role.name }}</span>
      <span v-if="role.image_url && modeOf(role) !== 'text'" class="pilot-role-image-wrap">
        <img class="pilot-role-image" :src="role.image_url" :alt="role.name" />
      </span>
    </span>
    <!-- Lives inside row links (pilot lists), so the click must not navigate. -->
    <button
      v-if="hiddenCount"
      class="pilot-roles__toggle"
      type="button"
      :aria-expanded="expanded"
      :title="expanded ? t('ui.roles.collapse') : t('ui.roles.showAll', { count: list.length })"
      @click.stop.prevent="expanded = !expanded"
    >
      {{ expanded ? t('ui.roles.collapse') : `+${hiddenCount}` }}
    </button>
  </span>
</template>

<style scoped>
.pilot-roles {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-width: 0;
  max-width: 100%;
  vertical-align: middle;
}

/* Long role names shorten; the full name is in the tooltip. */
.pilot-role-text {
  max-width: 13em;
}

.pilot-role-image {
  border-radius: 4px;
}

.pilot-role-badge.is-extra {
  animation: pilot-role-in 260ms var(--ease-ios) both;
}

@keyframes pilot-role-in {
  from {
    opacity: 0;
    transform: translateY(3px) scale(0.92);
  }
}

.pilot-roles__toggle {
  display: inline-flex;
  align-items: center;
  min-height: 1.35em;
  padding: 2px 7px;
  border: 1px solid var(--c-line-strong);
  border-radius: 999px;
  background: var(--c-sunken);
  color: var(--c-text-2);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 0.72em;
  font-weight: 700;
  line-height: 1.1;
  white-space: nowrap;
  transition: border-color var(--dur-2), color var(--dur-2), background-color var(--dur-2);
}

.pilot-roles__toggle:hover {
  border-color: var(--c-blue-line);
  background: var(--c-blue-soft);
  color: var(--c-accent-text);
}

.pilot-roles__toggle:focus-visible {
  outline: 2px solid var(--bm-cyan);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .pilot-role-badge.is-extra {
    animation: none;
  }
}
</style>
