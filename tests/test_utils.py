import os
from src import utils


def test_replace():
  test_file = "test_replace.txt"
  original_content = "This is a test file with some content."

  # Create test file
  with open(test_file, 'w') as f:
    f.write(original_content)

  # Replace part of the content
  utils.replace(test_file, 5, 7, "was")

  # Verify the replacement
  with open(test_file, 'r') as f:
    modified_content = f.read()

  print(f"Original: {original_content}")
  print(f"Modified: {modified_content}")

  # Clean up
  os.remove(test_file)


def test_search_and_replace():
  # Create a test file
  test_file = "test_file.txt"
  with open(test_file, "w") as f:
    f.write("This is a test file with some content.\n"
            "It contains multiple lines of text.\n"
            "We'll search for 'content' and replace it.\n")

  # Test replacing a string that exists
  utils.search_and_replace("content", "REPLACED", test_file)
  with open(test_file, "r") as f:
    assert "REPLACED" in f.read()

  # Test replacing a string that doesn't exist
  utils.search_and_replace("nonexistent", "should_not_appear", test_file)
  with open(test_file, "r") as f:
    assert "should_not_appear" not in f.read()

  # Clean up
  os.remove(test_file)
  print("All search_and_replace tests passed!")


def test_apply_changes():
  initial_content = '''
# some randome comment here

def greeting(name):
  print(f"Hello {name}!")


# some random comment after the possible change
    '''.strip()

  file_name = 'hello_world.py'
  project_path = '.'
  file_path = os.path.join(project_path, file_name)

  # Test valid changes application
  with open(file_path, 'w') as f:
    f.write(initial_content)

  valid_changes = f"""
```{file_name}
<<<<<< SEARCH
def greeting(name):
  print(f"Hello {{name}}!")
======
def greeting():
  print("Hello World!")
>>>>>> REPLACE
```
  """.strip()

  result = utils.apply_all(valid_changes, str(project_path))
  assert result == 0, "Valid changes should return success code 0"

  with open(file_path) as f:
    content = f.read()
    assert "def greeting():" in content
    assert "print(\"Hello World!\")" in content
    assert "name" not in content

  # Test atomic rollback when invalid changes
  invalid_changes = f"""
```{file_name}
<<<<<< SEARCH
def greeting():
  print("Hello World!")
======
def updated_greeting():
  print("Updated greeting!")
>>>>>> REPLACE
<<<<<< SEARCH
# non-existent pattern to force failure
======
# this replacement should never happen
>>>>>> REPLACE
```
  """.strip()

  result = utils.apply_all(invalid_changes, str(project_path))
  assert result == 1, "Invalid changes should return error code 1"

  # Verify content remains from first valid change
  with open(file_path) as f:
    content = f.read()
    assert "def greeting():" in content
    assert "print(\"Hello World!\")" in content
    assert "updated_greeting" not in content

  os.remove(file_path)


def test_hidden_files_ignored():
  """Test if files starting with a dot (hidden files) are properly ignored."""
  # Create test directory structure
  test_dir = "test_hidden_dir"
  os.makedirs(test_dir, exist_ok=True)

  # Create a regular file and a hidden file with the same content
  unique_content = f"UNIQUE_CONTENT_{os.urandom(4).hex()}"
  regular_file = os.path.join(test_dir, "regular_file.txt")
  hidden_file = os.path.join(test_dir, ".hidden_file.txt")

  with open(regular_file, 'w') as f:
    f.write(unique_content)

  with open(hidden_file, 'w') as f:
    f.write(unique_content)

  # Get all files in the directory using utils function
  all_files = utils.list_files(test_dir)

  # Verify only regular file is included, hidden file is excluded
  abs_regular = os.path.abspath(regular_file)
  abs_hidden = os.path.abspath(hidden_file)
  
  assert abs_regular in all_files, "Regular file should be included in results"
  assert abs_hidden not in all_files, "Hidden file should not be included in results"

  # Clean up
  os.remove(regular_file)
  os.remove(hidden_file)
  os.rmdir(test_dir)

  print("Hidden files exclusion test passed!")
