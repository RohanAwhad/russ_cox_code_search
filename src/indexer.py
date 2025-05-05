import os

from loguru import logger
from typing import Tuple, Optional
from watchdog.observers.api import BaseObserver

# first-party
from src import code_search, file_watcher, utils


def index_project(
    project_path: str,
    watch: bool = False) -> Tuple[code_search.TrigramRegexSearcher, dict[int, str], Optional[BaseObserver]]:
  """
    Index all files in the project, respecting .gitignore.
    If watch=True, returns an active file watcher observer.
    """
  project_path = os.path.abspath(project_path)
  searcher = code_search.TrigramRegexSearcher()

  ignore_patterns = utils.get_ignore_patterns(project_path)

  file_id = 0
  file_mapping: dict[int, str] = {}

  logger.info("Indexing project files...")
  for root, dirs, files in os.walk(project_path):
    # Filter out directories that should be ignored
    dirs[:] = [d for d in dirs if not utils.should_ignore(os.path.join(root, d), project_path, ignore_patterns)]

    for file in files:
      file_path = os.path.join(root, file)
      if utils.should_ignore(file_path, project_path, ignore_patterns):
        continue

      try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
        searcher.add_document(file_id, content)
        file_mapping[file_id] = os.path.relpath(file_path, project_path)
        file_id += 1
      except Exception as e:
        logger.error(f"Skipping {file_path}: {str(e)}")

  logger.info(f"Indexed {file_id} files.")

  # Set up watcher if requested
  observer = None
  if watch:
    observer = file_watcher.create_file_watcher(project_path, searcher, file_mapping)

  return searcher, file_mapping, observer
