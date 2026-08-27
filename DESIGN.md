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
- 2026-08-23 — news autoplay: the main-menu carousel advances on a configurable interval (30 seconds by default), pauses after manual navigation (5 minutes by default), and keeps the pinned published item first.
- 2026-08-23 — pilot analytics: profiles share one switchable statistics card for best laps, recent results, and a rating chart; the controls use existing card, pill, select, and chart tokens and show the qualifying/race source beside each lap.
- 2026-08-23 — chart polish: the rating trend uses a crisp, aspect-ratio-preserving SVG with a smoothed path, non-scaling stroke, and subtle gradient fill; track records show the session source beside each best lap.
- 2026-08-23 — race weather and schedule: races use separate registration-start, registration-end, and race-time values; the main card centres race time, keeps the green registration badge in the information area, and exposes the selected weather image there with a native tooltip containing all probabilities and track temperature.
- 2026-08-23 — weather imagery: admins choose separate light/dark images per weather condition; calendar and main-card weather indicators reuse the asset for the active theme without a framed weather section.
- 2026-08-24 — main-card geometry: restored the legacy date tile and three-column race-card proportions; schedule data remains available in the race details instead of changing the compact card layout.
- 2026-08-24 — main-card registration dates: the left date tile shows the registration-start value without a label, while the central end-registration tile uses a wider grid track and wraps its caption; simulator/class badges sit above a vertically centred, content-sized single-line track chip with ellipsis, while the main card shows only a small leading-weather image and race format details remain on the race-information page.
- 2026-08-24 — main-card weather and registration actions: the weather image is unframed and its native tooltip shows the dominant condition probability plus track temperature; registration cancellation and admin/moderator pilot removal stay on the race-information page rather than the compact card.
- 2026-08-24 — ACC manual results: the existing manual result table is available alongside ACC JSON upload, while the shared results endpoint accepts either input before the race is finished.
- 2026-08-24 — ACC manual qualification: the ACC manual form captures a qualifying lap beside race time/laps/best lap; the stored result exposes both race and qualification tabs using the existing results table.
- 2026-08-24 — ACC result car IDs and race numbers: result parsing normalizes numeric `carModel` values from nested or flat ACC payloads, while race and team registration reject number 000 in the API and form.
- 2026-08-24 — race-result penalties: applied time/SR penalties are bold danger-colour controls in the results table; selecting one opens and focuses the matching penalty in the existing penalty list modal.
- 2026-08-24 — race-result podium: the first three finishers use three ordered information columns (P1 centered/tallest), preserving the existing gold/silver/bronze surfaces; the detailed table starts at position 4.
- 2026-08-24 — race-result podium rating: each race-result podium column also shows the existing positive/negative RER change badge; qualification columns omit it because rating is applied to the race result.
- 2026-08-24 — race-result podium gradient: increased the existing medal-colour gradient opacity and spread only inside the three race-result columns for clearer separation without changing their palette.
- 2026-08-27 — admin safety controls: the system-admin row is read-only in the admin UI, bulk deletion is system-admin-only with a separate password, and host destruction stays outside the browser in favour of a verified SSH backup script.
- 2026-08-28 — result profiles and SR: result names link to pilot profiles; SR is rebuilt from the configured per-race value multiplied by each pilot's finished-race count, with penalties reapplied, while moderation cards no longer render e-mail addresses.
- 2026-08-28 — expected track laps: the existing race-assets editor stores an optional per-track expected average lap in milliseconds, with token-based admin inputs accepting `m:ss.mmm`; race details and track cards expose the value alongside measured averages.

## Components
- `frontend/src/pages/AdminUserList.vue` — administration page with theme-specific logo, default-avatar, system-setting, and per-simulator rating controls (loading is represented by disabled upload actions; empty state uses bundled defaults).
- `frontend/src/App.vue` — existing application shell, navigation, and theme-specific brand logo.
- `frontend/src/components/ImageCropper.vue` — reusable fixed-ratio crop dialog for selected raster images.
- `frontend/src/pages/MainMenu.vue` — main race filter bar with a compact native dropdown plus centred race time, in-card registration badge, and weather tooltip.
- `frontend/src/components/RaceAssetsEditor.vue` — admin ACC car-model mapping rows with editable IDs, add/remove controls, and responsive collapse.
- `frontend/src/components/AuditLogPanel.vue` — compact, refreshable staff audit history panel with explicit empty and error states.
- `frontend/src/pages/NewsManage.vue` — news editor with single-item pin controls and pinned-first management ordering.
- `frontend/src/pages/RaceDetails.vue` — moderator-only pilot removal action in the individual registration list, with confirmation and refreshed pagination.
- `frontend/src/pages/NewsManage.vue` — autoplay interval/pause settings plus single-pinned-news state reconciliation after saves.
- `frontend/src/components/ProfileAnalytics.vue` — reusable profile statistics block with simulator filter, best-lap source labels, recent result links, and an SVG rating trend.
- `frontend/src/pages/PilotList.vue` — track records table with the qualifying/race source for each selected best lap.
- `frontend/src/pages/ProfileEdit.vue` — favorite-car selector populated from the admin race-assets catalog.
- `frontend/src/pages/RaceEdit.vue` — separate registration-start, registration-end, and race-time controls plus weather probability and track-temperature inputs.
- `frontend/src/pages/RaceCalendar.vue` — selected race cards with schedule and leading-weather imagery.
- `frontend/src/pages/AdminUserList.vue` — admin weather-condition light/dark image uploads and previews.
- `frontend/src/components/RaceAssetsEditor.vue` — per-track expected average lap inputs with format guidance and validation.

## Non-Goals
- No Figma sync
- No image generation
- No framework or styling migration
