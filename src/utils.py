import fnmatch
import os
import re

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


def apply_all(changes: str, project_path: str) -> None:
  """
  Parse and apply multiple search and replace blocks from the given changes string.

  Args:
    changes: A string containing multiple code blocks with search/replace sections
    project_path: The base path of the project where files should be modified
  """

  # Extract code blocks
  code_block_pattern = r'```(.*?)\n(.*?)```'
  blocks = re.findall(code_block_pattern, changes, re.DOTALL)

  if not blocks:
    logger.warning("No code blocks found in the changes")
    return

  logger.info(f"Found {len(blocks)} code blocks to process")

  for file_path_with_content, content in blocks:
    # Extract the file path from the first line
    file_path = file_path_with_content.strip()
    if not file_path:
      logger.warning("Skipping block with no file path")
      continue

    # Parse search and replace blocks
    search_replace_pattern = r'<<<<<<< SEARCH\n(.*?)=======\n(.*?)>>>>>>> REPLACE'
    search_replace_blocks = re.findall(search_replace_pattern, content, re.DOTALL)

    if not search_replace_blocks:
      logger.warning(f"No search/replace blocks found in block for {file_path}")
      continue

    # Create full file path
    full_file_path = os.path.join(project_path, file_path.lstrip('/'))

    # Ensure the file path exists
    if not os.path.exists(full_file_path):
      logger.warning(f"No file exists at: {full_file_path}")
      continue

    logger.info(f"Processing {len(search_replace_blocks)} search/replace blocks for {file_path}")

    # Apply each search/replace block
    for search_text, replace_text in search_replace_blocks:
      try:
        search_and_replace(search_text, replace_text, full_file_path)
        logger.info(f"Applied changes to {file_path}")
      except Exception as e:
        logger.error(f"Error applying changes to {file_path}: {str(e)}")
