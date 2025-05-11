import asyncio
import argparse
import hashlib
import json
from pathlib import Path

# third-party
from pydantic_ai import Agent
from loguru import logger

# first-party
from src import utils

agent_system_prompt = '''
Analyze the provided file and generate a concise module-level docstring or header comment.
Write only the comment content without any delimiters (no triple quotes, no /* */, etc.).
Focus on the primary purpose and key functionalities.
Keep it to one sentence unless absolutely necessary.
'''.strip()

agent = Agent(
    'google-gla:gemini-2.0-flash',
    system_prompt=agent_system_prompt,
)


async def process_file(file_path: Path, content: str, md5_hash: str):
  try:
    logger.info(f"Processing {file_path}")
    result = await agent.run(f"Code to analyze:\n{content}")

    if not result.output:
      logger.warning(f"No docstring generated for {file_path}")
      return None

    return {"filepath": str(file_path.resolve()), "md5": md5_hash, "docstring": result.output.strip()}
  except Exception as e:
    logger.error(f"Error processing {file_path}: {str(e)}")
    return None


async def main():
  parser = argparse.ArgumentParser(description='Generate docstrings for Python files')
  parser.add_argument('project_path', type=str, help='Path to the project directory')
  args = parser.parse_args()

  project_path = args.project_path
  all_files = utils.list_files(project_path)

  # Load existing docstrings
  output_path = Path(project_path) / "docstrings.json"
  existing_docstrings = {}
  if output_path.exists():
    try:
      with open(output_path, "r") as f:
        existing_docstrings = json.load(f)
    except Exception as e:
      logger.error(f"Error loading existing docstrings: {e}")

  files_to_process = []
  for file_path in all_files:
    try:
      file_path = Path(file_path)
      content = file_path.read_text()
      md5_hash = hashlib.md5(content.encode()).hexdigest()
      existing_entry = existing_docstrings.get(str(file_path.resolve()), None)
      if existing_entry and existing_entry.get("MD5 hash") == md5_hash:
        logger.debug(f"Skipping {file_path} (hash unchanged)")
        continue
      files_to_process.append((file_path, content, md5_hash))
    except Exception as e:
      logger.error(f"Error reading {file_path}: {str(e)}")

  tasks = [process_file(fp, cont, hash) for fp, cont, hash in files_to_process]
  results = await asyncio.gather(*tasks)

  # Merge new results into existing docstrings
  for result in results:
    if result:
      existing_docstrings[result["filepath"]] = {
          "MD5 hash": result["md5"],
          "filepath": result["filepath"],
          "docstring": result["docstring"]
      }

  # Save merged docstrings
  with open(output_path, "w") as f:
    json.dump(existing_docstrings, f, indent=2)

  logger.info(f"Docstring generation complete. Results saved to {output_path}")


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    logger.warning("Operation cancelled by user")
  except Exception as e:
    logger.error(f"Fatal error: {str(e)}")
    raise
