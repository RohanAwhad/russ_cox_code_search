import os
import time
import random
import string
import argparse
import re
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
from src import indexer


def generate_random_pattern(length=3):
  return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def extract_realistic_patterns(searcher, file_mapping, project_path, num_queries=50):
  """Extract actual code snippets from the codebase to use as queries"""
  patterns = []
  files = list(file_mapping.items())

  if not files:
    return []

  for _ in range(num_queries):
    doc_id, rel_path = random.choice(files)
    content = searcher.docs[doc_id]

    if len(content) < 10:
      continue

    # Pick a random position and extract 1-3 lines
    pos = random.randint(0, len(content) - 10)

    # Find line boundaries
    start = content.rfind('\n', 0, pos) + 1
    end_lines = 1 + random.randint(0, 2)  # 1-3 lines

    end = pos
    for _ in range(end_lines):
      next_end = content.find('\n', end + 1)
      if next_end == -1:
        break
      end = next_end

    if end <= start:
      end = min(start + 100, len(content))

    snippet = content[start:end].strip()

    # Skip if too short or too long
    if len(snippet) < 5 or len(snippet) > 200:
      continue

    # Escape regex special chars
    snippet = re.escape(snippet)
    patterns.append(snippet)

  return patterns


def benchmark(project_path, num_queries=100):
  console = Console()

  # Measure indexing time
  console.print("[bold]Indexing project...[/bold]")
  t0 = time.time()
  searcher, file_mapping, _ = indexer.index_project(project_path, watch=False)
  indexing_time = time.time() - t0

  # Get document stats
  num_files = len(file_mapping)
  total_size = sum(len(searcher.docs[doc_id]) for doc_id in searcher.docs)

  console.print("[bold]Generating test queries...[/bold]")
  # Half random patterns, half realistic patterns
  num_random = num_queries // 2
  num_realistic = num_queries - num_random

  random_patterns = [generate_random_pattern(length=49) for _ in range(num_random)]
  realistic_patterns = extract_realistic_patterns(searcher, file_mapping, project_path, num_realistic)

  # If we couldn't extract enough realistic patterns, fill with random ones
  if len(realistic_patterns) < num_realistic:
    random_patterns.extend([generate_random_pattern() for _ in range(num_realistic - len(realistic_patterns))])

  patterns = random_patterns + realistic_patterns
  random.shuffle(patterns)

  # Run the benchmark
  console.print("[bold]Running benchmark queries...[/bold]")
  search_times = []
  hits = []
  for pattern in tqdm(patterns):
    t0 = time.time()
    results = searcher.search(pattern)
    search_time = time.time() - t0
    search_times.append(search_time)
    hits.append(len(results))

  # Calculate statistics
  avg_time = sum(search_times) / len(search_times) if search_times else 0
  min_time = min(search_times) if search_times else 0
  max_time = max(search_times) if search_times else 0
  avg_hits = sum(hits) / len(hits) if hits else 0

  # Results
  table = Table(title=f"Benchmark Results for {project_path}")
  table.add_column("Metric", style="cyan")
  table.add_column("Value", style="green")

  table.add_row("Files indexed", f"{num_files:,}")
  table.add_row("Total content size", f"{total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
  table.add_row("Indexing time", f"{indexing_time:.2f} seconds")
  table.add_row("Queries executed", f"{len(patterns)}")
  table.add_row("Avg search time", f"{avg_time * 1000:.2f} ms")
  table.add_row("Min search time", f"{min_time * 1000:.2f} ms")
  table.add_row("Max search time", f"{max_time * 1000:.2f} ms")
  table.add_row("Avg hits per query", f"{avg_hits:.2f}")

  # print query length
  avg_time = sum(search_times) / len(search_times) if search_times else 0
  min_time = min(search_times) if search_times else 0
  max_time = max(search_times) if search_times else 0
  avg_hits = sum(hits) / len(hits) if hits else 0
  avg_query_length = sum(len(p) for p in patterns) / len(patterns) if patterns else 0
  table.add_row("Avg query length", f"{avg_query_length:.2f} chars")

  console.print(table)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Benchmark code search on a large codebase')
  parser.add_argument('project_path', help='Path to the project to index')
  parser.add_argument('--queries', type=int, default=100, help='Number of queries to run')
  args = parser.parse_args()

  benchmark(args.project_path, args.queries)
