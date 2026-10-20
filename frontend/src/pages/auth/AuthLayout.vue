<script setup>
// Two-panel layout for sign-in and registration: the form on a glass card,
// a visual companion panel beside it (stacked under the form on phones).
import RacingLines from '../../ui/fx/RacingLines.vue'
</script>

<template>
  <div class="auth ui-shell ui-shell--wide">
    <section class="auth__form ui-glass ui-glass--strong">
      <slot />
    </section>
    <aside class="auth__aside ui-carbon">
      <RacingLines class="auth__lines" :count="12" />
      <!-- Optional full-bleed decoration behind the panel content. -->
      <slot name="backdrop" />
      <div class="auth__aside-inner">
        <slot name="aside" />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: clamp(14px, 2vw, 22px);
  align-items: stretch;
  padding-block: clamp(20px, 3vw, 36px) clamp(40px, 6vw, 72px);
}

.auth__form {
  display: grid;
  align-content: start;
  gap: 22px;
  padding: clamp(20px, 3.4vw, 44px);
  border-radius: var(--r-xl);
}

.auth__aside {
  position: relative;
  min-height: 560px;
  overflow: hidden;
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-1);
}

.auth__aside::before {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(70% 55% at 80% 10%, color-mix(in srgb, var(--bm-blue) 34%, transparent), transparent 70%),
    radial-gradient(60% 50% at 10% 100%, color-mix(in srgb, var(--bm-blue-deep) 40%, transparent), transparent 70%);
  content: '';
}

.auth__lines {
  opacity: 0.8;
}

.auth__aside-inner {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: center;
  gap: 24px;
  height: 100%;
  padding: clamp(22px, 3.4vw, 44px);
}

@media (max-width: 980px) {
  .auth {
    grid-template-columns: minmax(0, 1fr);
  }

  .auth__aside {
    min-height: 0;
  }
}
</style>
