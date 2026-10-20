<script setup>
// SVG filters behind the `.ui-ink` class (design/fx.css), mounted once in
// App.vue. They turn a track diagram's brightness into opacity, so its white
// sheet disappears and only the lines stay: light ink in the dark theme (the
// image is inverted first), dark ink in the light one. In the light filter the
// pixel's own alpha carries the constant, so the empty bars beside a contained
// image stay empty.
</script>

<template>
  <svg class="ink-filters" width="0" height="0" aria-hidden="true" focusable="false">
    <filter id="ui-ink-dark" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0.47 1.57 0.16 0 0" />
    </filter>
    <filter id="ui-ink-light" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  -0.47 -1.57 -0.16 2.2 0" />
    </filter>
  </svg>
</template>

<style scoped>
.ink-filters {
  position: absolute;
  width: 0;
  height: 0;
}
</style>
