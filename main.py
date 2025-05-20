import asyncio
import json
import os
import sys
import re
from typing import Any, Dict

from loguru import logger
from watchdog.observers.api import BaseObserver

from src import utils
from src.code_search import TrigramRegexSearcher
from src.indexer import trgm
from src.indexer import semantic
from src.pubsub import PubSub


class ServerHandler:

  def __init__(self):
    self.project_path: str = ''
    self.observer: BaseObserver | None = None
    self.file_mapping: dict[int, str] = {}
    self.path_to_id: dict[str, int] = {}
    self.searcher: TrigramRegexSearcher | None = None
    self.docstrings: dict[str, dict[str, str]] = {}


  def initialize(self, project_path: str) -> Dict[str, Any]:
    """Initialize the searcher with the given project path"""
    try:
      self.project_path = os.path.abspath(project_path)
      if not os.path.isdir(self.project_path):
        return {"error": f"Invalid directory: {project_path}"}

      pubsub = PubSub()

      # Get ignore patterns and initialize
      self.ignore_patterns = utils.get_ignore_patterns(self.project_path)

      # Subscribe to file events
      pubsub.subscribe("file_created", self._handle_file_event)
      pubsub.subscribe("file_modified", self._handle_file_event)
      pubsub.subscribe("file_deleted", self._handle_file_event)

      logger.info(f"Initializing index for {self.project_path}")

      self.searcher, self.file_mapping, self.observer = trgm.index_project(self.project_path, watch=True, pubsub=pubsub)

      logger.info("No docstrings found. Building...")
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      try:
        docstrings, _ = loop.run_until_complete(semantic.index_project_semantic(self.project_path))
        self.docstrings = docstrings
        logger.info(f"Docstrings generated with {len(self.docstrings)} entries")
      except Exception as e:
        logger.error(f"Failed to generate docstrings: {e}")
        return {"error": f"Docstring generation failed: {e}"}
      finally:
        loop.close()
        logger.info(f"Loaded {len(self.docstrings)} docstrings")
        return {"status": "initialized", "files_indexed": len(self.file_mapping), "project_path": self.project_path}

    except Exception as e:
      logger.exception("Initialization error")
      return {"error": str(e)}

  def _index_file(self, file_path):
    rel_path = os.path.relpath(file_path, self.project_path)
    if utils.should_ignore(file_path, self.project_path, self.ignore_patterns):
      return

    try:
      with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

      # If file exists in index, update it
      if rel_path in self.path_to_id:
        file_id = self.path_to_id[rel_path]
        # Remove old trigrams
        old_content = self.searcher.docs.get(file_id, "")
        for i in range(len(old_content) - 2):
          tg = old_content[i:i + 3]
          if tg in self.searcher.inv:
            self.searcher.inv[tg].discard(file_id)
        # Add new content
        self.searcher.add_document(file_id, content)
      else:
        # Add new file
        file_id = self.next_id
        self.next_id += 1
        self.searcher.add_document(file_id, content)
        self.file_mapping[file_id] = rel_path
        self.path_to_id[rel_path] = file_id

    except Exception as e:
      logger.error(f"Error indexing {file_path}: {str(e)}")

  def _delete_file(self, file_path):
    rel_path = os.path.relpath(file_path, self.project_path)
    if rel_path in self.path_to_id:
      file_id = self.path_to_id[rel_path]
      # Remove from index
      if file_id in self.searcher.docs:
        del self.searcher.docs[file_id]
      # Remove from all trigram posting lists
      for docs in self.searcher.inv.values():
        docs.discard(file_id)
      # Update mappings
      del self.file_mapping[file_id]
      del self.path_to_id[rel_path]

  def _handle_file_event(self, event_type, file_path):
    if event_type == "file_created":
      self._index_file(file_path)
    elif event_type == "file_modified":
      self._index_file(file_path)
    elif event_type == "file_deleted":
      self._delete_file(file_path)

  def search(self, request: dict[str, str | int]) -> Dict[str, Any]:
    """Search for the given pattern"""
    if "pattern" not in request:
      return {"error": "Missing search pattern"}

    max_results: int = int(request.get("max_results", 100))
    pattern: str = str(request['pattern'])
    try:
      if not self.searcher:
        return {"error": "Searcher not initialized"}

      # Process pattern (allow raw regex with r: prefix)
      if not pattern.startswith('r:'):
        pattern = re.escape(pattern)
      else:
        pattern = pattern[2:]

      results = self.searcher.search(pattern)

      matches = []
      for doc_id in results[:max_results]:
        file_path = self.file_mapping[doc_id]
        abs_path = os.path.join(self.project_path, file_path)

        try:
          with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

          # Find matches in the file
          match_positions = []
          for m in re.finditer(pattern, content):
            context_start = max(0, m.start() - 50)
            context_end = min(len(content), m.end() + 50)

            # Calculate line number
            line_number = content.count('\n', 0, m.start()) + 1

            match_positions.append({
                "start": m.start(),
                "end": m.end(),
                "line": line_number,
                "context": content[context_start:context_end]
            })

          matches.append({
              "file": file_path,
              "matches":
                  match_positions[:5]  # Limit matches per file
          })
        except Exception as e:
          logger.error(f"Error processing file {file_path}: {e}")

      return {"status": "success", "total_matches": len(results), "returned_matches": len(matches), "matches": matches}
    except Exception as e:
      logger.exception("Search error")
      return {"error": str(e)}

  def shutdown(self) -> Dict[str, Any]:
    """Stop the file watcher and clean up resources"""
    try:
      if self.observer:
        self.observer.stop()
        self.observer.join()
        self.observer = None
      return {"status": "shutdown"}
    except Exception as e:
      logger.exception("Shutdown error")
      return {"error": str(e)}

  def apply_changes(self, request) -> Dict[str, Any]:
    if "changes" not in request:
      return {"error": "Missing changes parameter"}

    did_apply = utils.apply_all(request["changes"], self.project_path)
    if did_apply == 0:
      return {"status": "success", "message": "Changes applied successfully"}

    return {"status": "error", "message": "Failed to apply changes. No changes were made."}


def read_message():
  """Read a message using LSP-like protocol"""
  content_length = 0

  # Read headers
  while True:
    line = sys.stdin.readline().strip()
    if not line:
      break

    if line.startswith("Content-Length: "):
      content_length = int(line[16:])

  # Read content
  if content_length > 0:
    content = sys.stdin.read(content_length)
    return content

  return None


def write_message(response):
  """Write a message using LSP-like protocol"""
  content = json.dumps(response)
  message = f"Content-Length: {len(content)}\n\n{content}"
  sys.stdout.write(message)
  sys.stdout.flush()


def main():

  server = None
  try:
    if len(sys.argv) != 2:
      sys.stderr.write("Usage: python main.py <project_path>\n")
      sys.exit(1)

    project_path = sys.argv[1]
    server = ServerHandler()

    # Initialize with the project path
    init_result = server.initialize(project_path)
    write_message(init_result)

    # Main loop
    while True:
      try:
        message = read_message()
        if not message:
          continue

        request = json.loads(message)

        if "command" not in request:
          write_message({"error": "Missing command"})
          continue

        if request["command"] == "search":
          result = server.search(request)
          write_message(result)

        elif request["command"] == "apply_changes":
          result = server.apply_changes(request)
          write_message(result)

        elif request["command"] == "shutdown":
          result = server.shutdown()
          write_message(result)
          break

        else:
          write_message({"error": f"Unknown command: {request['command']}"})

      except json.JSONDecodeError:
        write_message({"error": "Invalid JSON"})
      except Exception as e:
        logger.exception("Error processing message")
        write_message({"error": str(e)})

  except KeyboardInterrupt:
    if server:
      server.shutdown()
    logger.info("Server stopped by user")
  except Exception as e:
    logger.exception("Unhandled exception")
    sys.stderr.write(f"Error: {str(e)}\n")
    sys.exit(1)


if __name__ == "__main__":
  main()
