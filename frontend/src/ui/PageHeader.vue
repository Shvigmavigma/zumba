<script setup>
// Page heading used across the site: mono eyebrow, wide display title that
// rises letter by letter, optional lead copy, actions and a side note.
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  lead: { type: String, default: '' },
  /** Heading level for the title (1 for pages, 2 inside pages). */
  level: { type: Number, default: 1 },
  compact: { type: Boolean, default: false }
})
</script>

<template>
  <header class="page-header" :class="{ 'page-header--compact': compact }">
    <div class="page-header__main">
      <p v-if="eyebrow" v-reveal="{ y: 8, blur: 0, duration: 700 }" class="ui-eyebrow ui-eyebrow--accent page-header__eyebrow">
        <span class="page-header__tick" aria-hidden="true"></span>{{ eyebrow }}
      </p>
      <component :is="`h${level}`" v-split class="ui-display page-header__title">{{ title }}</component>
      <p v-if="lead" v-reveal="{ delay: 180, y: 10 }" class="ui-lead page-header__lead">{{ lead }}</p>
      <slot name="below" />
    </div>
    <div v-if="$slots.actions || $slots.aside" v-reveal="{ delay: 240, y: 10 }" class="page-header__side">
      <slot name="aside" />
      <div v-if="$slots.actions" class="page-header__actions"><slot name="actions" /></div>
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px 32px;
}

.page-header__main {
  display: grid;
  flex: 1 1 520px;
  gap: 12px;
  min-width: 0;
}

.page-header__tick {
  width: 18px;
  height: 2px;
  border-radius: 2px;
  background: var(--bm-blue-bright);
}

.page-header__title {
  color: var(--c-text);
  font-size: var(--fs-h1);
  overflow-wrap: anywhere;
}

.page-header--compact .page-header__title {
  font-size: var(--fs-h2);
}

.page-header__lead {
  max-width: 68ch;
}

.page-header__side {
  display: grid;
  justify-items: end;
  gap: 14px;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 760px) {
  .page-header__side {
    justify-items: start;
    width: 100%;
  }

  .page-header__actions {
    justify-content: flex-start;
  }
}
</style>
