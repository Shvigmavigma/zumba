# Design System

## Stack
- framework: Vue 3 + Vite
- styling: global CSS with custom properties (`frontend/src/styles.css`)
- components: Vue single-file components
- animation: CSS transitions
- icons: lucide-vue-next

## Tokens
- brand: `--primary`, `--primary-strong`, `--accent`
- backgrounds: `--bg`, `--panel`, `--panel-muted`
- logo preview: `--logo-preview-dark`
- text: `--text`, `--muted`
- shape: `--card-radius`, `--control-radius`
- shadow: `--shadow`
- themes: `:root` and `:root[data-theme='dark']`

## Decisions
- 2026-08-22 — init: existing Vue/Vite stack and CSS token system documented; no Tailwind or unused utility layer added.
- 2026-08-22 — theme logos: admin controls reuse the existing card, field, button, border, background, `--logo-preview-dark`, and responsive tokens; uploaded light/dark assets update the shared brand state immediately.
- 2026-08-22 — logo cropper: raster logos use the existing banner crop visual language and a 780x200 output matching the header slot; pointer, keyboard, zoom, disabled, and responsive states are included.

## Components
- `frontend/src/pages/AdminUserList.vue` — administration page with theme-specific logo upload and preview controls (loading is represented by disabled upload actions; empty state uses bundled default logos).
- `frontend/src/App.vue` — existing application shell, navigation, and theme-specific brand logo.
- `frontend/src/components/ImageCropper.vue` — reusable fixed-ratio crop dialog for selected raster images.

## Non-Goals
- No Figma sync
- No image generation
- No framework or styling migration
