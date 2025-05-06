import fnmatch
import os

from pathlib import Path
from typing import List
from loguru import logger


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


def replace(file_path: str, start_idx: int, end_idx: int, replace_with: str) -> None:
  """Replace content in file from start_idx to end_idx with replace_with."""
  with open(file_path, 'r') as f:
    content = f.read()

  new_content = content[:start_idx] + replace_with + content[end_idx:]

  with open(file_path, 'w') as f:
    f.write(new_content)


def search_and_replace(search_str: str, replace_str: str, file_path: str) -> None:
  """Search for content in file and replace all occurrences."""
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      content = f.read()

    if search_str not in content:
      logger.debug(f"'{search_str}' not found in {file_path}")
      return

    new_content = content.replace(search_str, replace_str)
    with open(file_path, 'w', encoding='utf-8') as f:
      f.write(new_content)

    logger.debug(f"Replaced all occurrences of '{search_str}' in {file_path}")
  except Exception as e:
    logger.error(f"Error replacing in {file_path}: {str(e)}")
