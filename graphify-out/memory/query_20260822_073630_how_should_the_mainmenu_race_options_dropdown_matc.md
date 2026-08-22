---
type: "query"
date: "2026-08-22T07:36:30.834582+00:00"
question: "How should the MainMenu race options dropdown match neighboring controls?"
contributor: "graphify"
source_nodes: ["MainMenu.vue", "raceGameFilter", "raceStatusFilter"]
---

# Q: How should the MainMenu race options dropdown match neighboring controls?

## Answer

The MainMenu race options summary belongs to the same filter cluster as raceGameFilter. Reuse the existing form-control typography and --text color: IBM Plex Sans, 15px, weight 400, normal line height. Runtime computed styles now exactly match the adjacent select.

## Source Nodes

- MainMenu.vue
- raceGameFilter
- raceStatusFilter