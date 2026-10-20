<script setup>
// The race page's two columns: the main one (entry form, results, entries)
// and the side panels (briefing, weather, penalties, fan vote). When the
// results ask for the whole width, the side panels leave like an app being
// closed on a phone — they swing towards the viewer on their left edge, drift
// right and are gone by 40 degrees — and the main column takes their place.
// On a narrow screen the panels sit under the main column and stay there.
defineProps({
  /** The main column has the page's whole width; the side panels are away. */
  expanded: { type: Boolean, default: false },
  /** There is no main column: the side panels are the page. */
  asideOnly: { type: Boolean, default: false }
})
</script>

<template>
  <div class="race-layout" :class="{ 'is-expanded': expanded && !asideOnly, 'is-aside-only': asideOnly }">
    <div v-if="!asideOnly" class="race-layout__main"><slot name="main" /></div>
    <aside class="race-layout__aside">
      <div class="race-layout__panels"><slot name="aside" /></div>
    </aside>
  </div>
</template>

<style scoped>
.race-layout {
  --race-aside: clamp(320px, 28vw, 400px);
  --race-gap: clamp(16px, 2vw, 24px);
  /* How long the side panels take to leave. Long enough for the turn to be seen: they are half gone at 20 degrees, gone at 40. */
  --race-fold: 620ms;
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--race-aside);
  align-items: start;
  gap: var(--race-gap);
  transition: grid-template-columns var(--dur-3) var(--ease-ios), column-gap var(--dur-3) var(--ease-ios);
}

.race-layout__main,
.race-layout__panels {
  display: grid;
  align-content: start;
  gap: var(--race-gap);
  min-width: 0;
}

.race-layout__aside {
  min-width: 0;
  /* The panels turn in depth; the viewer stands in front of their middle. */
  perspective: 1400px;
}

.race-layout__panels {
  transform-origin: left center;
  /* Coming back: the column opens first, the panels settle into it. */
  transition:
    transform var(--race-fold) var(--ease-ios) 90ms,
    opacity var(--dur-3) var(--ease-out) 130ms,
    filter var(--dur-3) var(--ease-out) 130ms,
    visibility 0s;
}

.race-layout.is-aside-only {
  grid-template-columns: minmax(0, 1fr);
}

.is-aside-only .race-layout__panels {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

@media (min-width: 1181px) {
  /* The panels keep their width while their column closes, so nothing in them reflows on the way out,
     and they hold on to the page's right edge: the main column grows under them instead of pushing them off. */
  .race-layout:not(.is-aside-only) .race-layout__aside {
    display: flex;
    justify-content: flex-end;
  }

  .race-layout:not(.is-aside-only) .race-layout__panels {
    flex: none;
    width: var(--race-aside);
  }

  /* Leaving: the panels start to turn, then the main column grows into their place under them. */
  .race-layout.is-expanded {
    grid-template-columns: minmax(0, 1fr) 0px;
    column-gap: 0px;
    transition: grid-template-columns var(--race-fold) var(--ease-ios) 140ms, column-gap var(--race-fold) var(--ease-ios) 140ms;
  }

  .is-expanded .race-layout__aside {
    height: 0;
    pointer-events: none;
  }

  .is-expanded .race-layout__panels {
    opacity: 0;
    filter: blur(5px);
    transform: translate3d(26%, 0, 0) rotateY(-40deg) scale(1.06);
    /* Out of reach of the keyboard and screen readers once it has left. */
    visibility: hidden;
    transition:
      transform var(--race-fold) cubic-bezier(0.45, 0, 0.55, 1),
      opacity var(--race-fold) cubic-bezier(0.4, 0, 1, 1),
      filter var(--race-fold) cubic-bezier(0.4, 0, 1, 1),
      visibility 0s linear var(--race-fold);
  }
}

@media (max-width: 1180px) {
  .race-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .race-layout__panels {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    align-items: start;
  }
}

@media (max-width: 640px) {
  .race-layout__panels,
  .is-aside-only .race-layout__panels {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .race-layout,
  .race-layout.is-expanded,
  .race-layout__panels,
  .is-expanded .race-layout__panels {
    transition: none;
  }

  .is-expanded .race-layout__panels {
    filter: none;
    transform: none;
  }
}
</style>
