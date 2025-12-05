#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai>=1.0",
#     "numpy>=1.24",
#     "aiofiles>=23.2",
#     "python-dotenv>=1.0",
# ]
# ///
"""
NeurIPS Abstract Embedding Enrichment

Generates OpenAI embeddings for abstracts and computes pairwise similarity
to enable "Find Similar" functionality in the viewer.

Usage:
    # Generate embeddings + compute similarity (skip cached)
    uv run scripts/enrich_embeddings.py

    # Force regenerate all embeddings
    uv run scripts/enrich_embeddings.py --force

    # Only recompute similarity from cached embeddings
    uv run scripts/enrich_embeddings.py --similarity-only

    # Preview what would be done
    uv run scripts/enrich_embeddings.py --dry-run
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import aiofiles
import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load .env file from project root (for OPENAI_API_KEY)
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# OpenAI embedding model - small is cheap ($0.02/1M tokens) and good quality
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# How many similar abstracts to store per abstract
TOP_K_SIMILAR = 30


def get_paths(year: int) -> tuple[Path, Path, Path]:
    """Get paths for papers JSON, embeddings cache, and similarity output."""
    papers_file = DATA_DIR / f"neurips-{year}-orals-posters.json"
    embeddings_dir = DATA_DIR / "embeddings"
    similarity_file = DATA_DIR / f"similarity_{year}.json"
    return papers_file, embeddings_dir, similarity_file


def build_embedding_text(paper: dict) -> str:
    """
    Build composite text for embedding.

    Combines multiple fields to capture semantic meaning:
    - Title and authors for content + network similarity
    - Keywords for topical similarity
    - Topic for conference-assigned clustering
    - Abstract text (truncated) for detailed content
    """
    # Format authors
    authors_list = paper.get('authors', [])
    if isinstance(authors_list, list):
        authors_str = ', '.join(a.get('fullname', '') for a in authors_list if isinstance(a, dict))
    else:
        authors_str = str(authors_list)

    parts = [
        paper.get('name', ''),  # title
        authors_str,
        ' '.join(paper.get('keywords', []) or []),
        paper.get('topic', ''),
        paper.get('decision', ''),
        # Truncate abstract text to stay under token limits (~8k for embedding model)
        (paper.get('abstract', '') or '')[:2000],
    ]
    return '\n'.join(filter(None, parts))


def save_json_atomic(filepath: Path, data: dict) -> None:
    """Save JSON with consistent formatting using atomic write."""
    content = json.dumps(data, indent=2, ensure_ascii=False)
    tmp_path = filepath.with_suffix('.json.tmp')
    tmp_path.write_text(content, encoding='utf-8')
    tmp_path.rename(filepath)


class EmbeddingEnricher:
    def __init__(self, year: int, max_concurrent: int = 50):
        self.year = year
        self.papers_file, self.embeddings_dir, self.similarity_file = get_paths(year)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        self.client: Optional[AsyncOpenAI] = None  # Lazy init
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.total_tokens = 0

    def _ensure_client(self):
        """Lazily initialize OpenAI client when needed."""
        if self.client is None:
            self.client = AsyncOpenAI()
        return self.client

    def load_papers(self) -> list[dict]:
        """Load all papers from the NeurIPS JSON file."""
        if not self.papers_file.exists():
            logger.error(f"Papers file not found: {self.papers_file}")
            return []

        with open(self.papers_file) as f:
            data = json.load(f)

        papers = data.get('results', [])
        logger.info(f"Loaded {len(papers)} papers from {self.papers_file.name}")
        return papers

    def get_cached_embedding(self, paper_id: str | int) -> Optional[list[float]]:
        """Load cached embedding if it exists."""
        # Sanitize paper_id for filename (replace / and other problematic chars)
        safe_id = str(paper_id).replace('/', '_')
        cache_file = self.embeddings_dir / f"{safe_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    return data.get('embedding')
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    async def generate_embedding(self, text: str, paper_id: str | int,
                                  dry_run: bool = False) -> Optional[list[float]]:
        """Generate embedding for text using OpenAI API."""
        if dry_run:
            return None

        async with self.semaphore:
            try:
                client = self._ensure_client()
                response = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text,
                )
                embedding = response.data[0].embedding
                self.total_tokens += response.usage.total_tokens

                # Cache the embedding
                safe_id = str(paper_id).replace('/', '_')
                cache_file = self.embeddings_dir / f"{safe_id}.json"
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps({
                        'paper_id': paper_id,
                        'model': EMBEDDING_MODEL,
                        'embedding': embedding,
                    }))

                return embedding

            except Exception as e:
                logger.error(f"Failed to embed {paper_id}: {e}")
                return None

    async def process_paper(self, paper: dict, index: int, total: int,
                            start_time: float, force: bool = False,
                            dry_run: bool = False) -> tuple[str | int, Optional[list[float]]]:
        """Process a single paper - check cache or generate embedding."""
        paper_id = paper['id']

        # Check cache first (unless force)
        if not force:
            cached = self.get_cached_embedding(paper_id)
            if cached:
                self.skipped += 1
                return paper_id, cached

        # Build text and generate embedding
        text = build_embedding_text(paper)
        if not text.strip():
            logger.warning(f"Empty text for {paper_id}")
            self.failed += 1
            return paper_id, None

        embedding = await self.generate_embedding(text, paper_id, dry_run=dry_run)

        if dry_run:
            self.success += 1  # Count as success for dry-run
        elif embedding:
            self.success += 1
        else:
            self.failed += 1

        # Progress logging
        done = index + 1
        if done % 100 == 0 or done == total:
            elapsed = time.time() - start_time
            rate = (self.success + self.skipped) / elapsed if elapsed > 0 else 0
            logger.info(
                f"Progress: {done}/{total} "
                f"(new: {self.success}, cached: {self.skipped}, failed: {self.failed}) "
                f"[{rate:.1f}/s]"
            )

        return paper_id, embedding

    def compute_similarity(self, embeddings: dict[str, list[float]],
                           dry_run: bool = False) -> dict[str, list[str]]:
        """
        Compute top-K similar papers for each paper.

        Uses cosine similarity with numpy for efficiency.
        """
        paper_ids = list(embeddings.keys())
        n = len(paper_ids)

        if n == 0:
            return {}

        logger.info(f"Computing similarity matrix for {n} papers...")

        # Build embedding matrix
        matrix = np.array([embeddings[pid] for pid in paper_ids], dtype=np.float32)

        # Normalize for cosine similarity (so dot product = cosine sim)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        matrix_normalized = matrix / norms

        # Compute similarity in batches to manage memory
        similarity = {}
        batch_size = 500

        for i in range(0, n, batch_size):
            batch_end = min(i + batch_size, n)
            batch = matrix_normalized[i:batch_end]

            # Compute similarities for this batch against all
            sims = batch @ matrix_normalized.T  # (batch_size, n)

            for j, idx in enumerate(range(i, batch_end)):
                paper_id = paper_ids[idx]
                row = sims[j]

                # Get top-K+1 (excluding self)
                top_indices = np.argsort(row)[::-1][:TOP_K_SIMILAR + 1]

                # Filter out self and convert to paper_ids
                similar_ids = [
                    paper_ids[k] for k in top_indices
                    if paper_ids[k] != paper_id
                ][:TOP_K_SIMILAR]

                similarity[paper_id] = similar_ids

            if batch_end % 1000 == 0 or batch_end == n:
                logger.info(f"Similarity progress: {batch_end}/{n}")

        return similarity

    async def run(self, force: bool = False, similarity_only: bool = False,
                  dry_run: bool = False, max_papers: Optional[int] = None):
        """Run the embedding enrichment pipeline."""

        if dry_run:
            logger.info("=== DRY RUN MODE - No files will be written ===")

        # Load papers
        logger.info(f"Loading papers from {self.papers_file}...")
        papers = self.load_papers()

        if not papers:
            logger.error("No papers loaded. Exiting.")
            return

        if max_papers:
            papers = papers[:max_papers]
            logger.info(f"Limited to {max_papers} papers for testing")

        # Count existing embeddings
        existing = set(
            f.stem for f in self.embeddings_dir.glob("*.json")
        )
        logger.info(f"Found {len(existing)} cached embeddings")

        embeddings: dict[str, list[float]] = {}

        if not similarity_only:
            # Generate embeddings
            logger.info("Generating embeddings...")
            start_time = time.time()

            tasks = [
                self.process_paper(p, i, len(papers), start_time,
                                   force=force, dry_run=dry_run)
                for i, p in enumerate(papers)
            ]

            results = await asyncio.gather(*tasks)

            for paper_id, embedding in results:
                if embedding:
                    embeddings[paper_id] = embedding

            elapsed = time.time() - start_time
            logger.info(
                f"Embedding complete: {self.success} new, {self.skipped} cached, "
                f"{self.failed} failed in {elapsed:.1f}s"
            )

        # Load all cached embeddings for similarity computation
        if not dry_run:
            logger.info("Loading all cached embeddings...")
            for f in self.embeddings_dir.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        paper_id = data['paper_id']
                        if paper_id not in embeddings:
                            embeddings[paper_id] = data['embedding']
                except (json.JSONDecodeError, KeyError):
                    pass

            logger.info(f"Total embeddings loaded: {len(embeddings)}")

            # Compute similarity
            similarity = self.compute_similarity(embeddings)

            # Save similarity file
            logger.info(f"Saving similarity data to {self.similarity_file}...")
            save_json_atomic(self.similarity_file, similarity)

            size_mb = self.similarity_file.stat().st_size / 1024 / 1024
            logger.info(f"Saved {self.similarity_file.name} ({size_mb:.2f} MB)")

        # Summary
        logger.info("")
        logger.info("=== ENRICHMENT COMPLETE ===")
        logger.info(f"  Embeddings generated: {self.success}")
        logger.info(f"  Embeddings cached: {self.skipped}")
        logger.info(f"  Embeddings failed: {self.failed}")
        logger.info(f"  Total with embeddings: {len(embeddings)}")
        if self.total_tokens > 0:
            # text-embedding-3-small costs $0.02 per 1M tokens
            cost = self.total_tokens * 0.02 / 1_000_000
            logger.info(f"  Tokens used: {self.total_tokens:,}")
            logger.info(f"  Estimated cost: ${cost:.4f}")
        logger.info(f"  Similarity file: {self.similarity_file}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate embeddings and compute similarity for NeurIPS papers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate embeddings + compute similarity (skip cached)
  %(prog)s

  # Force regenerate all embeddings
  %(prog)s --force

  # Only recompute similarity from cached embeddings
  %(prog)s --similarity-only

  # Preview what would be done
  %(prog)s --dry-run

  # Test with subset
  %(prog)s --max 100
        """
    )
    parser.add_argument('--year', type=int, default=2025,
                        help='NeurIPS year (default: 2025)')
    parser.add_argument('--force', action='store_true',
                        help='Regenerate all embeddings (ignore cache)')
    parser.add_argument('--similarity-only', action='store_true',
                        help='Only recompute similarity from cached embeddings')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be done without writing files')
    parser.add_argument('--max', type=int, default=None,
                        help='Max papers to process (for testing)')
    parser.add_argument('--workers', type=int, default=50,
                        help='Concurrent API requests (default: 50)')

    args = parser.parse_args()

    # Check for API key
    if not os.environ.get('OPENAI_API_KEY') and not args.dry_run and not args.similarity_only:
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.error("Options to set it:")
        logger.error("  1. Add to .env file: OPENAI_API_KEY=sk-...")
        logger.error("  2. Export in shell: export OPENAI_API_KEY='sk-...'")
        return

    enricher = EmbeddingEnricher(year=args.year, max_concurrent=args.workers)
    await enricher.run(
        force=args.force,
        similarity_only=args.similarity_only,
        dry_run=args.dry_run,
        max_papers=args.max,
    )


if __name__ == "__main__":
    asyncio.run(main())
