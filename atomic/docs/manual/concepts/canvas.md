---
title: Canvas
description: Spatial visualization of your knowledge graph using semantic and tag relationships.
---

Canvas is a spatial visualization of your knowledge graph. It gives you a bird's-eye view of atoms, tags, clusters, and semantic relationships.

## Force Simulation

Atoms are positioned using several forces:

- **Link force** - Atoms sharing tags are linked together.
- **Similarity force** - Semantically related atoms are pulled closer together.
- **Charge force** - Repulsion prevents atoms from overlapping.
- **Center force** - Keeps the graph centered in the viewport.

## Persistent Layout

Atom positions are saved to the database, so the layout is stable across sessions. When you reopen the canvas, atoms stay where you placed them.

Atomic has both persisted atom positions and computed graph data. The canvas-level APIs can return aggregated nodes when a graph is too large to render atom by atom.

## Interaction

- **Zoom and pan** - Navigate the graph with mouse or trackpad.
- **Click** - Select an atom to view its content.
- **Drag** - Reposition atoms manually.
- **Filter** - Scope the canvas to specific tags.

## Graph APIs

Canvas and graph views use these API groups:

- `GET /api/canvas/positions`
- `PUT /api/canvas/positions`
- `GET /api/canvas/atoms-with-embeddings`
- `POST /api/canvas/level`
- `GET /api/canvas/global`
- `GET /api/graph/edges`
- `GET /api/graph/neighborhood/{atom_id}`
- `POST /api/graph/rebuild-edges`
- `POST /api/clustering/compute`
- `GET /api/clustering`

If the graph looks empty, check that embeddings and semantic edges have completed. Rebuilding edges queues recomputation for atoms with embeddings.

## Related

- [Semantic Search](/concepts/semantic-search/)
- [Tags](/concepts/tags/)
- [API Overview](/api/overview/)
