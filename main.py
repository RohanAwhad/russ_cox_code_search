import asyncio
import json
import os
import sys
import re
from typing import Any, Dict
import select

import subprocess
from loguru import logger
from src import utils

from src.indexer import trgm
from src.indexer.semantic import index_project_semantic


class CodeSearchServer:
    def __init__(self):
        pass

    def initialize(self, project_path: str) -> Dict[str, Any]:
        """Initialize the searcher with the given project path"""
        try:
            self.project_path = os.path.abspath(project_path)
            if not os.path.isdir(self.project_path):
                return {"error": f"Invalid directory: {project_path}"}

            logger.info(f"Initializing index for {self.project_path}")
            self.searcher, self.file_mapping, self.observer = trgm.index_project(
                self.project_path, watch=True
            )

            logger.info("No docstrings found. Building...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                docstrings, _ = loop.run_until_complete(
                    index_project_semantic(self.project_path)
                )
                self.docstrings = docstrings
                logger.info(f"Docstrings generated with {len(self.docstrings)} entries")
            except Exception as e:
                logger.error(f"Failed to generate docstrings: {e}")
                return {"error": f"Docstring generation failed: {e}"}
            finally:
                loop.close()
                logger.info(f"Loaded {len(self.docstrings)} docstrings")
                return {
                    "status": "initialized",
                    "files_indexed": len(self.file_mapping),
                    "project_path": self.project_path,
                }

        except Exception as e:
            logger.exception("Initialization error")
            return {"error": str(e)}

    def search(self, pattern: str, max_results: int = 100) -> Dict[str, Any]:
        """Search for the given pattern"""
        try:
            if not self.searcher:
                return {"error": "Searcher not initialized"}

            # Process pattern (allow raw regex with r: prefix)
            if not pattern.startswith("r:"):
                pattern = re.escape(pattern)
            else:
                pattern = pattern[2:]

            results = self.searcher.search(pattern)

            matches = []
            for doc_id in results[:max_results]:
                file_path = self.file_mapping[doc_id]
                abs_path = os.path.join(self.project_path, file_path)

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Find matches in the file
                    match_positions = []
                    for m in re.finditer(pattern, content):
                        context_start = max(0, m.start() - 50)
                        context_end = min(len(content), m.end() + 50)

                        # Calculate line number
                        line_number = content.count("\n", 0, m.start()) + 1

                        match_positions.append(
                            {
                                "start": m.start(),
                                "end": m.end(),
                                "line": line_number,
                                "context": content[context_start:context_end],
                            }
                        )

                    matches.append(
                        {
                            "file": file_path,
                            "matches": match_positions[:5],  # Limit matches per file
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

            return {
                "status": "success",
                "total_matches": len(results),
                "returned_matches": len(matches),
                "matches": matches,
            }
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
        server = CodeSearchServer()

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
                    if "pattern" not in request:
                        write_message({"error": "Missing search pattern"})
                        continue

                    max_results = request.get("max_results", 100)
                    result = server.search(request["pattern"], max_results)
                    write_message(result)

                elif request["command"] == "apply_changes":
                    if "changes" not in request:
                        write_message({"error": "Missing changes parameter"})
                        continue

                    did_apply = utils.apply_all(request["changes"], project_path)
                    if did_apply == 0:
                        write_message(
                            {
                                "status": "success",
                                "message": "Changes applied successfully",
                            }
                        )
                    else:
                        write_message(
                            {
                                "status": "error",
                                "message": "Failed to apply changes. No changes were made.",
                            }
                        )

                elif request["command"] == "test":
                    script_path = os.path.join(project_path, ".dingllm/run_tests.sh")

                    if not os.path.isfile(script_path):
                        write_message({"error": "Test script not found"})
                        return

                    try:
                        process = subprocess.Popen(
                            ["bash", script_path],
                            cwd=project_path,
                            text=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            bufsize=1,  # Line buffered
                            env={
                                **os.environ,
                                "PYTHONUNBUFFERED": "1",
                                "STDBUF_I": "0",
                                "STDBUF_O": "0",
                                "STDBUF_E": "0",
                            },
                        )

                        # Create file descriptor lists for select
                        stdout_fd = process.stdout.fileno()
                        stderr_fd = process.stderr.fileno()
                        readable = {
                            stdout_fd: process.stdout,
                            stderr_fd: process.stderr,
                        }

                        while readable:
                            # Wait for data to be available on either stdout or stderr
                            ready, _, _ = select.select(readable, [], [])

                            for fd in ready:
                                line = readable[fd].readline()
                                if not line:  # EOF
                                    readable.pop(fd)
                                    continue

                                if fd == stdout_fd:
                                    write_message(
                                        {"type": "stdout", "output": line.strip()}
                                    )
                                else:
                                    write_message(
                                        {"type": "stderr", "output": line.strip()}
                                    )

                            # Check if process has exited and all output has been read
                            if process.poll() is not None and not readable:
                                break

                        write_message(
                            {"status": "success", "return_code": process.returncode}
                        )

                    except Exception as e:
                        write_message({"error": str(e)})

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
