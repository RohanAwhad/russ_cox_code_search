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

  # Check if file or directory is hidden (starts with .)
  basename = os.path.basename(path)
  if basename.startswith('.'):
    return True

  # Check path components for hidden directories
  path_parts = rel_path.split(os.sep)
  for part in path_parts:
    if part.startswith('.'):
      return True

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
  ignore_patterns.extend([
      '.git/',
      '.idea/',
      '*__pycache__/',
      '*.pyc',
      '*.pyo',
      '*.so',
      '*.o',
      '*.obj',
      '*.DS_Store',
      '*node_modules',
      '*.venv',
      '*.jpg',
      '*.png',
      '*uv.lock',
      '*.swp',
      '*.swo',
      '*.log',
      '*.mypy_cache',
      # Ignore all hidden files and directories (starting with .)
      '.*',
      '.*/',
  ])

  return ignore_patterns


def replace(file_path: str, start_idx: int, end_idx: int, replace_with: str) -> None:
  """Replace content in file from start_idx to end_idx with replace_with."""
  with open(file_path, 'r') as f:
    content = f.read()

  new_content = content[:start_idx] + replace_with + content[end_idx:]

  with open(file_path, 'w') as f:
    f.write(new_content)


def search_and_replace(search_str: str, replace_str: str, file_path: str) -> int:
  """Search for content in file and replace all occurrences."""
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      content = f.read()

    if search_str not in content:
      logger.debug(f"'{search_str}' not found in {file_path}")
      return 1

    new_content = content.replace(search_str, replace_str)
    with open(file_path, 'w', encoding='utf-8') as f:
      f.write(new_content)

    logger.debug(f"Replaced all occurrences of '{search_str}' in {file_path}")
    return 0
  except Exception as e:
    logger.error(f"Error replacing in {file_path}: {str(e)}")
    return 1


def apply_all(changes: str, project_path: str) -> int:
  """Parse and apply multiple search and replace blocks from the given changes string atomically.
    Returns 0 if all changes were applied successfully, 1 otherwise."""
  # Extract code blocks
  code_block_pattern = r'```(.*?)\n(.*?)```'
  blocks = re.findall(code_block_pattern, changes, re.DOTALL)

  if not blocks:
    logger.warning("No code blocks found in the changes")
    return 1

  logger.info(f"Found {len(blocks)} code blocks to process")

  files_to_modify = {}
  files_to_create = {}
  search_replace_pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)>>>>>>> REPLACE'

  # First pass: validate and categorize blocks
  for file_path_with_content, content in blocks:
    file_path = file_path_with_content.strip()
    if not file_path:
      logger.warning("Skipping block with no file path")
      return 1

    full_file_path = os.path.join(project_path, file_path.lstrip('/'))

    # Parse search/replace blocks
    search_replace_blocks = re.findall(search_replace_pattern, content, re.DOTALL)

    if not search_replace_blocks:
      # Check if file exists to determine if we should create it
      if os.path.exists(full_file_path):
        logger.warning(f"No search/replace blocks found in block for existing file {file_path}")
        return 1
      files_to_create[full_file_path] = content
    else:
      # Validate existing file for modification
      if not os.path.exists(full_file_path):
        logger.warning(f"No file exists at: {full_file_path}")
        return 1
      if full_file_path not in files_to_modify:
        files_to_modify[full_file_path] = []
      files_to_modify[full_file_path].extend(search_replace_blocks)

  # Create new files first
  try:
    for file_path, content in files_to_create.items():
      os.makedirs(os.path.dirname(file_path), exist_ok=True)
      with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
      logger.info(f"Created new file: {file_path}")
  except Exception as e:
    logger.error(f"Error creating file {file_path}: {str(e)}")
    return 1

  # Read original content of all files and prepare modified versions
  original_contents = {}
  modified_contents = {}
  for file_path, blocks in files_to_modify.items():
    try:
      with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    except Exception as e:
      logger.error(f"Error reading {file_path}: {str(e)}")
      return 1

    modified_content = original_content
    for search_text, replace_text in blocks:
      # Check if search_text exists in the current content
      if search_text not in modified_content:
        logger.error(f"Search pattern not found in {file_path}: {search_text}")
        return 1
      modified_content = modified_content.replace(search_text, replace_text)

    original_contents[file_path] = original_content
    modified_contents[file_path] = modified_content

  # Write all modified contents
  try:
    for file_path, content in modified_contents.items():
      with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
  except Exception as e:
    logger.error(f"Error writing to {file_path}: {str(e)}")
    # Restore all files
    for path, orig_content in original_contents.items():
      try:
        with open(path, 'w', encoding='utf-8') as f:
          f.write(orig_content)
      except Exception as e:
        logger.error(f"Error restoring {path}: {str(e)}")
    return 1

  return 0
