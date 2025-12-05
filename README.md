# NeurIPS 2025 Abstract Browser

Searchable browser for NeurIPS 2025 conference papers (orals and posters).

## What's here

- `scripts/build_viewer.py` - Generate searchable HTML viewer
- `scripts/enrich_embeddings.py` - Compute paper similarity using embeddings
- `data/neurips-2025-orals-posters.json` - 6,002 papers (orals + posters)

## Quick start

```bash
# Build viewer
uv run scripts/build_viewer.py

# Generate similarity data (requires OpenAI API key in .env)
uv run scripts/enrich_embeddings.py
```

## Viewer features

- Full-text search with word boundary / case sensitivity toggles
- Filter by topic, decision type (Oral/Poster/Spotlight), and day
- Find similar papers using embedding similarity
- Star papers for later reference (stored in browser)
- Keyboard navigation (j/k, /, s, Enter)
- Expand/collapse paper cards
- Mobile-optimized, dark mode support
