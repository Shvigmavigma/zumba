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
- 2026-08-22 — main race filters: the six race-property checkboxes remain inline on calendar/admin pages and use a native, keyboard-accessible dropdown only on the main menu.
- 2026-08-22 — main race filter typography: the dropdown trigger inherits the same font, line height, and `--text` color as neighboring form controls.
- 2026-08-22 — admin controls: per-user request limits, one common simulator RER coefficient, and SR-per-race amount are stored in `AppSetting`; default avatar reuses the existing admin card and cropper, with a square output and shared reactive fallback state.
- 2026-08-22 — ACC entrylist mapping: the admin race-assets card exposes editable numeric car-model IDs; exports warn about ACC and write the configured IDs to `carModel`/`forcedCarModel`.
- 2026-08-23 — audit and news controls: staff changes are shown in a compact admin audit card, while news uses a single pinned item as the main-menu default and wraps navigation at both ends.
- 2026-08-23 — race navigation: main-menu race cards keep their existing nested controls but expose the whole card as a keyboard-accessible link target with hover/focus affordances.
- 2026-08-23 — moderator registration control: pilot rows expose a compact destructive action only to admins/moderators and only before a race starts; team rows remain owner-managed.

## Components
- `frontend/src/pages/AdminUserList.vue` — administration page with theme-specific logo, default-avatar, system-setting, and per-simulator rating controls (loading is represented by disabled upload actions; empty state uses bundled defaults).
- `frontend/src/App.vue` — existing application shell, navigation, and theme-specific brand logo.
- `frontend/src/components/ImageCropper.vue` — reusable fixed-ratio crop dialog for selected raster images.
- `frontend/src/pages/MainMenu.vue` — main race filter bar with a compact native dropdown for qualification, format, and official-status options.
- `frontend/src/components/RaceAssetsEditor.vue` — admin ACC car-model mapping rows with editable IDs, add/remove controls, and responsive collapse.
- `frontend/src/components/AuditLogPanel.vue` — compact, refreshable staff audit history panel with explicit empty and error states.
- `frontend/src/pages/NewsManage.vue` — news editor with single-item pin controls and pinned-first management ordering.
- `frontend/src/pages/RaceDetails.vue` — moderator-only pilot removal action in the individual registration list, with confirmation and refreshed pagination.

## Non-Goals
- No Figma sync
- No image generation
- No framework or styling migration
