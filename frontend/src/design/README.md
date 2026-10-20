# BMRL design system (redesign 2026-10)

Dark-first "pit lane at night" with a mirrored light "paddock" theme. iOS-like
materials (glass, springs, large radii) carrying a racing vocabulary (start
lights, telemetry mono labels, track artwork, carbon weave).

**The brand blue `#1652d8` (`--bm-blue`) is the original BMRL colour. Never
replace it.** Use `--c-accent-text` for blue *text* (it lightens on dark).

## Files

| Path | Role |
| --- | --- |
| `src/styles.css` | Legacy styles, wrapped in `@layer legacy`. Anything unlayered wins. Do not edit for redesigned pages. |
| `src/design/tokens.css` | Colour, type, radius, motion tokens + bridge to legacy token names. |
| `src/design/base.css` | Document base, `ui-*` utilities: typography, glass, buttons, chips, dots, meters, skeleton, alerts, links. |
| `src/design/primitives.css` | Harmonises legacy `.button`, `.card`, inputs, `.pill`… for admin screens. |
| `src/design/components.css` | `ui-card`, `ui-section-head`, `ui-kv`, forms (`ui-input`…), `ui-table`, `ui-pos`, `ui-modal`. |
| `src/design/motion.css` | Route / popover / sheet / list transitions, View Transition theme switch. |
| `src/design/fx.css` | Styles for pointer directives, `ui-beam`, `ui-shiny`. |
| `src/ui/*` | Vue building blocks (below). |
| `src/shell/*` | Header, footer, mobile tab bar & sheet, settings, account menu, ⌘K palette. |
| `src/i18n/ui.js`, `src/i18n/pages/*.js` | Copy for new UI. Every file in `i18n/pages/` is merged automatically. |

## Tokens (most used)

- Surfaces: `--c-bg`, `--c-surface` (glass), `--c-surface-2`, `--c-surface-solid`, `--c-sunken`, `--c-elevated`
- Lines: `--c-line`, `--c-line-strong`, `--c-blue-line`; tints: `--c-blue-soft`
- Text: `--c-text`, `--c-text-2`, `--c-text-3`, `--c-accent-text`
- Brand & signal: `--bm-blue`, `--bm-blue-deep`, `--bm-blue-bright`, `--bm-cyan` (telemetry), `--bm-green`, `--bm-red`, `--bm-amber`, `--bm-gold/silver/bronze`
- Type: `--font-display` (Unbounded — uppercase headings, use with restraint), `--font-body` (Onest), `--font-mono` (JetBrains Mono — labels, times, numbers)
- Radius: `--r-xs 8`, `--r-sm 12`, `--r-md 16`, `--r-lg 22`, `--r-xl 30`, `--r-pill`
- Motion: `--ease-ios`, `--ease-out`, `--ease-spring`, `--dur-1..4`
- Layout: `.ui-shell` (+ `.ui-shell--wide`), `.ui-page` (vertical rhythm), `--gutter`, `--header-h`

## Utility classes

Typography `ui-eyebrow` (+`--accent`), `ui-display`, `ui-title`, `ui-lead`, `ui-mono`, `ui-num`, `ui-muted`, `ui-faint`.
Surfaces `ui-glass`, `ui-panel`, `ui-sunken`, `ui-carbon`, `ui-card`; `ui-dark` makes a block (and every token inside it) dark in both themes.
Buttons `ui-btn` + `--primary | --outline | --ghost | --danger` + `--sm | --lg | --icon | --block`.
Chips `ui-chip` + `--blue | --solid | --green | --red | --amber`; status dot `ui-dot` + `--green | --red | --blue | --amber` + `--live` (pulse).
Data `ui-meter` (set `--value` on the inner span), `ui-table-wrap > ui-table` (`.is-num`, `.is-center`), `ui-pos ui-pos--1/2/3`, `ui-kv`.
Forms `ui-form`, `ui-form-row`, `ui-input`, `ui-select`, `ui-textarea`, `ui-check`; dialogs `ui-modal-backdrop > ui-modal`.
Feedback `ui-alert` (+ `--info | --success`), `ui-skeleton`, `ui-shiny` (loading text).

## Directives (global)

- `v-reveal` / `v-reveal="120"` / `v-reveal="{ delay, y, blur, scale }"` — fade up out of blur on first view (anime.js). Element roots only.
- `v-split` — heading letters rise in (anime.js `splitText`). Use on 1 heading per block.
- `v-spotlight` — cursor light + lit border. Uses the element's `::before`/`::after`: don't combine with your own pseudo elements or `ui-beam`.
- `v-tilt="8"` — 3D tilt; add `<span class="ui-glare" />` inside for glare.
- `v-magnet="6"` — CTA leans toward the cursor. `v-spark` — click sparks.

## Components (`src/ui`)

`PageHeader` (eyebrow, title, lead, `#actions`, `#aside`, `#below`), `SegmentedControl` (v-model, options `{ value, label, icon?, count?, badge? }`), `SwitchToggle` (v-model), `Popover` (v-model:open, `#trigger="{ toggle }"`), `FormField` (label, hint, error, success, required, icon, count/max; slot gets `{ id, describedBy, invalid }`), `EmptyState` (icon, title, text, loading), `ActivityRings`.
FX: `fx/StartLights` (signature), `fx/CountUp`, `fx/RollingNumber`, `fx/Countdown`, `fx/RacingLines`, `fx/AmbientBackground`.
Shared race helpers: `src/raceDisplay.js`, `src/components/RaceRow.vue`; licence progress: `licenseProgress()` in `src/pilotDisplay.js`.

## Conventions

- Route meta `design: true` removes the legacy `.page` container; the page then wraps itself in `<div class="ui-page ui-shell ui-shell--wide">`.
- Keep page logic intact; restyle templates and move styles into `<style scoped>`. Give each page a single root element.
- New copy goes to `src/i18n/pages/<page>.js` (ru + en). Reuse existing `messages.js` keys where they fit.
- Eyebrows/numbering must mean something (real sequence, real category). Motion should be purposeful; everything honours `prefers-reduced-motion`.
- Reference implementation: `src/pages/MainMenu.vue` + `src/pages/home/*`.
