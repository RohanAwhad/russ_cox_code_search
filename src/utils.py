import fnmatch
import os

from pathlib import Path
from typing import List


def parse_gitignore(gitignore_path: Path) -> List[str]:
  """Parse the .gitignore file and return a list of patterns to ignore."""
  if not gitignore_path.exists():
    return []

  patterns = []
  with open(gitignore_path, 'r') as f:
    for line in f:
      line = line.strip()
      # Skip comments and empty lines
      if not line or line.startswith('#'):
        continue
      patterns.append(line)

  return patterns


def should_ignore(path: str, base_path: str, ignore_patterns: List[str]) -> bool:
  """Check if a file should be ignored based on .gitignore patterns."""
  rel_path = os.path.relpath(path, base_path)

  for pattern in ignore_patterns:
    # Handle negation patterns
    if pattern.startswith('!'):
      if fnmatch.fnmatch(rel_path, pattern[1:]):
        return False
    # Handle directory patterns
    elif pattern.endswith('/'):
      if fnmatch.fnmatch(rel_path + '/', pattern) or rel_path.startswith(pattern):
        return True
    # Handle file patterns
    elif fnmatch.fnmatch(rel_path, pattern):
      return True
    # Handle subdirectory matching
    elif '/' in pattern and '*' not in pattern:
      if rel_path.startswith(pattern):
        return True

  return False


def get_ignore_patterns(project_path: str) -> List[str]:
  """Get ignore patterns from .gitignore and add common patterns."""
  gitignore_path = Path(project_path) / '.gitignore'
  ignore_patterns = parse_gitignore(gitignore_path)

  # Add common patterns to always ignore
  ignore_patterns.extend(['.git/', '.idea/', '__pycache__/', '*.pyc', '*.pyo', '*.so', '*.o', '*.obj', '.DS_Store'])

  return ignore_patterns
