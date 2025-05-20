import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger
from src.utils import should_ignore, get_ignore_patterns
from src.pubsub import PubSub


class IndexUpdateHandler(FileSystemEventHandler):

  def __init__(self, searcher, file_mapping, project_path, ignore_patterns, pubsub: PubSub):
    self.searcher = searcher
    self.file_mapping = file_mapping
    self.project_path = project_path
    self.ignore_patterns = ignore_patterns
    self.pubsub = pubsub
    self.path_to_id = {path: id for id, path in file_mapping.items()}
    self.next_id = max(file_mapping.keys()) + 1 if file_mapping else 0

  def on_created(self, event):
    if event.is_directory or not event.src_path:
      return
    logger.info(f"File created: {event.src_path}")
    self.pubsub.publish("file_created", event.src_path)

  def on_modified(self, event):
    if event.is_directory or not event.src_path:
      return
    logger.info(f"File modified: {event.src_path}")
    self.pubsub.publish("file_modified", event.src_path)

    # Optional: Trigger reindexing of the file
    self._index_file(event.src_path)

  def on_deleted(self, event):
    if event.is_directory or not event.src_path:
      return
    logger.info(f"File deleted: {event.src_path}")
    self.pubsub.publish("file_deleted", event.src_path)

  def _index_file(self, file_path):
    rel_path = os.path.relpath(file_path, self.project_path)
    if should_ignore(file_path, self.project_path, self.ignore_patterns):
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
      logger.info(f"Indexed {rel_path}")

    except Exception as e:
      logger.error(f"Error indexing {file_path}: {str(e)}")


def create_file_watcher(project_path, searcher, file_mapping, pubsub: PubSub):
  project_path = os.path.abspath(project_path)
  ignore_patterns = get_ignore_patterns(project_path)

  event_handler = IndexUpdateHandler(searcher, file_mapping, project_path, ignore_patterns, pubsub)
  observer = Observer()
  observer.schedule(event_handler, project_path, recursive=True)
  observer.start()

  logger.info(f"Watching {project_path} for changes...")

  return observer
