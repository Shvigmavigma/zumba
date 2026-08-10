# bmrl-race-control DESIGN.md

> Auto-generated design system — reverse-engineered via static analysis by skillui.
> Frameworks: Vue 3.5.13
> Colors: 20 · Fonts: 1 · Components: 24
> Icon library: Lucide · State: not detected
> Primary theme: dark · Dark mode toggle: yes · Motion: subtle

---

## 1. Visual Theme & Atmosphere

This is a **dark-themed** interface with a warm tone. Depth is expressed through layered shadows and subtle surface color variation. Typography uses **Inter** throughout — a clean, modern choice that maintains consistency. Spacing follows a **4px base grid** (compact density), with scale: 2, 4, 6, 8, 10, 12, 14, 16px. The accent color **#f59e0b** anchors interactive elements (buttons, links, focus rings). Motion is subtle — smooth transitions (150-300ms) ease state changes without drawing attention.

---

## 2. Color Palette & Roles

| Token | Hex | Role | Use |
|---|---|---|---|
| background | `#040912` | background | Page background, darkest surface |
| surface | `#000000` | surface | Card and panel backgrounds |
| panel-muted | `#0d1420` | surface | Card and panel backgrounds |
| panel-muted | `#edf3fb` | surface | Card and panel backgrounds |
| primary-strong | `#ffffff` | text-primary | Headings and body text |
| muted | `#8f9db2` | text-muted | Captions, placeholders, secondary info |
| border | `#475569` | border | Dividers, card borders, outlines |
| accent | `#f59e0b` | accent | CTAs, links, focus rings, active states |
| danger | `#b45309` | danger | Error states, destructive actions |
| podium-color | `#d6a11f` | warning | Warning states, caution indicators |
| primary | `#2b7cff` | info | Informational highlights |
| primary-strong | `#041b40` | unknown | Palette color |
| podium-color | `#aeb7c2` | unknown | Palette color |
| primary | `#0a3475` | unknown | Palette color |
| podium-color | `#b87333` | unknown | Palette color |
| unknown | `#1652d8` | unknown | Palette color |
| unknown | `#0d2f8f` | unknown | Palette color |
| border | `#d5deeb` | unknown | Palette color |
| unknown | `#92400e` | unknown | Palette color |
| unknown | `#7c2d12` | unknown | Palette color |

### Dark Mode Token Mapping

| Variable | Light | Dark |
|---|---|---|
| `--bg` | `#f7faff` | `#02040a` |
| `--panel` | `#ffffff` | `#050914` |
| `--panel-muted` | `#f3f7ff` | `#0a1222` |
| `--text` | `#05070d` | `#ffffff` |
| `--muted` | `#24344f` | `#c8d3e5` |
| `--border` | `#c7d7fb` | `#173574` |
| `--primary-strong` | `var(--brand-blue-deep)` | `#ffffff` |
| `--danger` | `#ca2436` | `#fb4b5d` |
| `--success` | `#087a46` | `#22c55e` |
| `--track-line` | `rgba(10, 52, 117, 0.052)` | `rgba(43, 124, 255, 0.05)` |
| `--track-mark` | `rgba(31, 111, 255, 0.06)` | `rgba(43, 124, 255, 0.05)` |
| `--glass` | `rgba(255, 255, 255, 0.92)` | `rgba(5, 9, 20, 0.92)` |
| `--bg-top` | `#ffffff` | `#000000` |
| `--bg-bottom` | `#eaf1ff` | `#071326` |
| `--panel-shine` | `#ffffff` | `#0e1a30` |
| `--shadow` | `0 18px 42px rgba(13, 47, 143, 0.12)` | `0 18px 42px rgba(0, 0, 0, 0.34)` |
| `--race-surface` | `rgba(255, 255, 255, 0.96)` | `rgba(5, 9, 20, 0.95)` |
| `--race-surface-strong` | `color-mix(in srgb, var(--brand-blue) 8%, #ffffff)` | `color-mix(in srgb, var(--brand-blue) 14%, #050914)` |
| `--race-line` | `rgba(22, 82, 216, 0.18)` | `rgba(22, 82, 216, 0.24)` |
| `--race-warn` | `rgba(13, 47, 143, 0.14)` | `rgba(13, 47, 143, 0.18)` |

### CSS Variable Tokens

```css
--panel-muted: #edf3fb;
--muted: #53647d;
--border: #d5deeb;
--primary: #0a3475;
--primary-strong: #041b40;
--accent: #1f6fff;
--card-padding: 16px;
--card-radius: 8px;
```


---

## 3. Typography Rules

**Font Stack:**
- **Inter** — Heading 1, Heading 2, Heading 3, Body, Caption

| Role | Font | Size | Weight |
|---|---|---|---|
| Heading 1 | Inter | 48px / 3rem | 700 |
| Heading 2 | Inter | 32px / 2rem | 600 |
| Heading 3 | Inter | 24px / 1.5rem | 600 |
| Body | Inter | 16px / 1rem | 400 |
| Caption | Inter | 12px / 0.75rem | 400 |

**Typographic Rules:**
- Use **Inter** for all text — do not mix font families
- Maintain consistent hierarchy: no more than 3-4 font sizes per screen
- Headings use bold (600-700), body uses regular (400)
- Line height: 1.5 for body text, 1.2 for headings
- Use color and opacity for secondary hierarchy, not additional font sizes


---

## 4. Component Stylings

### Layout (1)

**MainMenu** — `src/pages/MainMenu.vue`
- Props: `pilots`, `completed_races`, `open_races`, `staff`
- Key Styles: `active:`

```tsx
{
  transform: `translate3d(${twitchWidgetPosition.value.x}px, ${twitchWidgetPosition.value.y}px, 0
```

### Navigation (4)

**PaginationControls** — `src/components/PaginationControls.vue`

**PilotList** — `src/pages/PilotList.vue`

**Profile** — `src/pages/Profile.vue`
- Props: `key`, `label`, `value`

```tsx
{
    key,
    label: profileFieldLabel(key
```

**RaceCalendar** — `src/pages/RaceCalendar.vue`
- Props: `label`, `item.value)`, `count`
- Key Styles: `active:`

```tsx
{
    value: String(championship.id
```

### Data Display (2)

**AvatarViewer** — `src/components/AvatarViewer.vue`

**HallOfFame** — `src/pages/HallOfFame.vue`
- Props: `pilots`, `teams`
- Key Styles: `active:`

### Data Input (11)

**RacePenaltyListModal** — `src/components/RacePenaltyListModal.vue`
- Props: `target_id`, `time_seconds`, `sr_penalty_value`, `description`

**AdminUserList** — `src/pages/AdminUserList.vue`
- Variants: `admin`, `timeout`
- Props: `fallback_video_url`, `fallback_video_title`

```tsx
dangerForm.value.confirmation.trim(
```

**ChampionshipList** — `src/pages/ChampionshipList.vue`
- Variants: `ACC`, `fia`
- Props: `name`, `datetime_start`, `track`, `server_link`, `has_qualification`, `scoring_system`, `pole_bonus_enabled`
- Key Styles: `filter`, `active:`

```tsx
{
  name: '',
  datetime_start: '',
  track: '',
  server_link: '',
  has_qualification: true,
  scoring_system: 'fia',
  pole_bonus_enabled: false
}
```

**FuelCalculator** — `src/pages/FuelCalculator.vue`

**Login** — `src/pages/Login.vue`
- Props: `login`, `password`

**NewsManage** — `src/pages/NewsManage.vue`
- Props: `title`, `body`, `is_published`, `file`

```tsx
news.id === updated.id ? updated : news
```

**ProfileEdit** — `src/pages/ProfileEdit.vue`
- Props: `country`, `games`

**RaceAdminList** — `src/pages/RaceAdminList.vue`
- Props: `limit`, `offset`, `status_filter`, `game_filter`

*...and 3 more data input components.*

### Feedback (1)

**BannerEdit** — `src/pages/BannerEdit.vue`
- Props: `width`, `height`

```tsx
cropper.value ? cropTargets[cropper.value.position] || cropTargets.top : cropTargets.top
```

### Other (5)

**CountryCombobox** — `src/components/CountryCombobox.vue`
- Props: `option`, `score`, `needle)`

```tsx
{ option, score: matchScore(option, needle
```

**PenaltyDetailsModal** — `src/components/PenaltyDetailsModal.vue`

**AppealModeration** — `src/pages/AppealModeration.vue`

**PilotDetails** — `src/pages/PilotDetails.vue`

**UserEditModeration** — `src/pages/UserEditModeration.vue`



---

## 5. Layout Principles

- **Base spacing unit:** 4px
- **Spacing scale:** 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24
- **Border radius:** 8px, 9px, 10px, 12px, 999px, inherit, 16px
- **Max content width:** 1680px

**Spacing as Meaning:**
| Spacing | Use |
|---|---|
| 4-8px | Tight: related items within a group |
| 12-16px | Medium: between groups |
| 24-32px | Wide: between sections |
| 48px+ | Vast: major section breaks |


---

## 6. Depth & Elevation

### Flat — subtle depth hints

- `inset 0 1px 0 rgba(255,255,255,0.62)`
- `inset 0 1px 0 rgba(255,255,255,0.68)`
- `inset 0 0 0 1px color-mix(in srgb,var(--primary) 42%,transparent)`

### Raised — cards, buttons, interactive elements

- `var(--shadow)`
- `0 0 0 4px color-mix(in srgb,var(--primary) 16%,transparent)`
- `0 0 0 4px rgba(255,255,255,0.18)`

### Floating — dropdowns, popovers, modals

- `0 8px 18px rgba(7,20,47,0.11)`
- `inset 0 0 0 1px rgba(255,255,255,0.18),0 6px 14px color-mix(in srgb,var(--avatar-color) 20%,transparent)`
- `0 8px 18px color-mix(in srgb,var(--primary) 22%,transparent)`

### Overlay — full-screen overlays, top-level dialogs

- `0 1px 0 rgba(7,20,47,0.05),0 14px 30px rgba(7,20,47,0.1)`
- `0 14px 28px color-mix(in srgb,var(--primary) 26%,transparent)`
- `0 18px 44px rgba(15,23,42,0.18)`

### Z-Index Scale

`0, 1, 2, 3, 4, 10, 30, 32, 60, 80, 1500, 2000, 2100`



---

## 7. Animation & Motion

This project uses **subtle motion**. Transitions smooth state changes without demanding attention.

### Motion Guidelines

- Duration: 150-300ms for micro-interactions, 300-500ms for page transitions
- Easing: `ease-out` for enters, `ease-in` for exits
- Always respect `prefers-reduced-motion`


---

## 8. Do's and Don'ts

### Do's

- Use `#f59e0b` for interactive elements (buttons, links, focus rings)
- Use `#040912` as the primary page background
- Use **Inter** for all UI text
- Follow the **4px** spacing grid for all margins, padding, and gaps
- Use the defined shadow tokens for elevation — see Section 6
- Use border-radius from the scale: 8px, 9px, 10px, 12px, 999px
- Reuse existing components from Section 4 before creating new ones
- Use **Lucide** for all icons
- Always use CSS variables for colors — never hardcode hex
- Test both light and dark modes for contrast

### Don'ts

- Don't introduce colors outside this palette — extend the design tokens first
- Don't mix font families — use Inter consistently
- Don't use arbitrary spacing values — stick to multiples of 4px
- Don't create custom box-shadow values outside the system tokens
- Don't use arbitrary border-radius values — pick from the defined scale
- Don't duplicate component patterns — check Section 4 first
- Don't mix icon libraries — consistency matters
- Don't use backdrop-blur or blur effects

### Anti-Patterns (detected from codebase)

- No blur or backdrop-blur effects
- No zebra striping on tables/lists


---

## 9. Responsive Behavior

| Name | Value | Source |
|---|---|---|
| breakpoint-1181px | 1181px | css |

**Approach:** Use `@media (min-width: ...)` queries matching the breakpoints above.


---

## 10. Agent Prompt Guide

Use these as starting points when building new UI:

### Build a Card

```
Background: #000000
Border: 1px solid #475569
Radius: 12px
Padding: 16px
Font: Inter
Use shadow tokens from Section 6.
```

### Build a Button

```
Primary: bg #f59e0b, text white
Ghost: bg transparent, border #475569
Padding: 8px 16px
Radius: 12px
Hover: opacity 0.9 or lighter shade
Focus: ring with #f59e0b
```

### Build a Page Layout

```
Background: #040912
Max-width: 1680px, centered
Grid: 4px base
Responsive: mobile-first, breakpoints from Section 9
```

### Build a Stats Card

```
Surface: #000000
Label: #8f9db2 (muted, 12px, uppercase)
Value: #ffffff (primary, 24-32px, bold)
Status: use success/warning/danger from Section 2
```

### Build a Form

```
Input bg: #040912
Input border: 1px solid #475569
Focus: border-color #f59e0b
Label: #8f9db2 12px
Spacing: 16px between fields
Radius: 12px
```

### General Component

```
1. Read DESIGN.md Sections 2-6 for tokens
2. Colors: only from palette
3. Font: Inter, type scale from Section 3
4. Spacing: 4px grid
5. Components: match patterns from Section 4
6. Elevation: shadow tokens
```
