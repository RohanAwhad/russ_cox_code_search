import os
import hashlib
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from loguru import logger
from pydantic_ai import Agent
from watchdog.observers.api import BaseObserver

# first-party
from src import utils, file_watcher

DOCSTRINGS_FN = '.dingllm/docstrings.json'

# Default agent system prompt
_AGENT_SYSTEM_PROMPT = '''
Analyze the provided file and generate a concise module-level docstring or header comment.
Write only the comment content without any delimiters (no triple quotes, no /* */, etc.).
Focus on the primary purpose and key functionalities.
Keep it to one sentence unless absolutely necessary.
'''.strip()


async def _process_file(file_path: Path, content: str, md5_hash: str, agent: Agent,
                        project_path: str) -> Optional[Dict[str, Any]]:
  """Process a single file to generate a docstring."""
  try:
    logger.info(f"Processing {file_path}")
    result = await agent.run(f"Code to analyze:\n{content}")

    if not result.output:
      logger.warning(f"No docstring generated for {file_path}")
      return None

    docstring = result.output.strip()
    relative_path = str(file_path.resolve().relative_to(project_path))

    return {"filepath": relative_path, "md5": md5_hash, "docstring": docstring}
  except Exception as e:
    logger.error(f"Error processing {file_path}: {str(e)}")
    return None


def load_existing_docstrings(project_path: str) -> Dict[str, Any]:
  """Load existing docstrings from the project's docstrings.json file."""
  output_path = Path(project_path) / DOCSTRINGS_FN
  if output_path.exists():
    try:
      with open(output_path, "r") as f:
        return json.load(f)
    except Exception as e:
      logger.error(f"Error loading existing docstrings: {e}")
  return {}


async def index_project_semantic(project_path: str,
                                 agent_model: str = "google-gla:gemini-2.0-flash",
                                 watch: bool = False) -> Tuple[Dict[str, Any], Optional[BaseObserver]]:
  """
    Index all files in the project by generating docstrings.
    If watch=True, returns an active file watcher observer.
    """
  project_path = os.path.abspath(project_path)

  # Initialize the AI agent
  agent = Agent(
      agent_model,
      system_prompt=_AGENT_SYSTEM_PROMPT,
  )

  try:
    # Load existing docstrings to avoid reprocessing unchanged files
    docstrings = load_existing_docstrings(project_path)

    # Get files to process
    all_files = utils.list_files(project_path)
    files_to_process = []

    for fp in all_files:
      try:
        file_path = Path(fp)
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if not content:
          continue

        md5_hash = hashlib.md5(content.encode()).hexdigest()
        relative_path_str = str(file_path.resolve().relative_to(project_path))
        existing_entry = docstrings.get(relative_path_str, None)

        if existing_entry and existing_entry.get("md5") == md5_hash:
          logger.debug(f"Skipping {file_path} (hash unchanged)")

          continue

        files_to_process.append((file_path, content, md5_hash))
      except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")

    logger.info(f"Processing {len(files_to_process)} files for docstring generation...")

    # Process files in batches
    tasks = [_process_file(fp, cont, hash, agent, project_path) for fp, cont, hash in files_to_process]
    results = await asyncio.gather(*tasks)

    # Update docstrings dictionary with new results
    for result in results:
      if result:
        docstrings[result["filepath"]] = {
            "md5": result["md5"],
            "filepath": result["filepath"],
            "docstring": result["docstring"]
        }

    # Save the updated docstrings
    output_path = Path(project_path) / DOCSTRINGS_FN
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
      json.dump(docstrings, f, indent=2)

    logger.info(f"Docstring generation complete. Results saved to {output_path}")

    # Set up file watcher if requested
    observer = None
    if watch:
      logger.warning("Docstring file watching not yet implemented")

    return docstrings, observer

  finally:
    pass
