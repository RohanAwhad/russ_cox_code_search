import os

from src.indexer import trgm


def test_index_project(tmpdir):
  # Create temporary project structure
  project_dir = tmpdir.mkdir("test_project")
  file1 = project_dir.join("file1.txt")
  file1.write("test content")
  subdir = project_dir.mkdir("subdir")
  file2 = subdir.join("file2.txt")
  file2.write("another file")

  # Calculate expected relative paths
  expected_paths = {
      os.path.relpath(str(file1), str(project_dir)),
      os.path.relpath(str(file2), str(project_dir)),
  }

  # Index the project
  searcher, file_mapping, observer = trgm.index_project(str(project_dir))

  # Verify results
  assert len(file_mapping) == 2
  assert set(file_mapping.values()) == expected_paths
  assert observer is None
