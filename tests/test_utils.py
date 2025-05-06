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
