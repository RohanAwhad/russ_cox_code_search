import asyncio
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.indexer.semantic import DOCSTRINGS_FN, index_project_semantic

# pylint: disable=W0621


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
  project_dir = tmp_path / "test_project"
  project_dir.mkdir()
  (project_dir / DOCSTRINGS_FN).parent.mkdir(parents=True, exist_ok=True)
  return project_dir


@pytest.fixture
def sample_file_content() -> str:
  return "def hello_world():\n  print('Hello, world!')"


@pytest.fixture
def sample_file(temp_project_dir: Path, sample_file_content: str) -> Path:
  file_path = temp_project_dir / "sample.py"
  file_path.write_text(sample_file_content)
  return file_path


@pytest.mark.asyncio
async def test_skip_processed_file_with_unchanged_hash(temp_project_dir: Path, sample_file: Path,
                                                       sample_file_content: str):
  # Initial run to process the file
  mock_agent_run = AsyncMock(return_value=AsyncMock(output="Initial docstring."))
  with patch("pydantic_ai.Agent.run", mock_agent_run):
    await index_project_semantic(str(temp_project_dir))

  # Check that the docstring file was created and contains the initial docstring
  docstrings_path = temp_project_dir / DOCSTRINGS_FN
  assert docstrings_path.exists()
  with open(docstrings_path, "r") as f:
    docstrings_data = json.load(f)

  relative_file_path = str(sample_file.relative_to(temp_project_dir))
  assert relative_file_path in docstrings_data
  assert docstrings_data[relative_file_path]["docstring"] == "Initial docstring."
  assert docstrings_data[relative_file_path]["md5"] == hashlib.md5(
      sample_file_content.encode()).hexdigest()

  # Reset mock for the second run
  mock_agent_run.reset_mock()
  mock_agent_run.return_value = AsyncMock(output="New docstring, should not be called.")

  # Second run, file content is unchanged
  with patch("pydantic_ai.Agent.run", mock_agent_run):
    await index_project_semantic(str(temp_project_dir))

  # Assert that agent.run was NOT called again for this file
  mock_agent_run.assert_not_called()

  # Verify docstring file still contains the original docstring
  with open(docstrings_path, "r") as f:
    docstrings_data_after_second_run = json.load(f)
  assert docstrings_data_after_second_run[relative_file_path]["docstring"] == "Initial docstring."

