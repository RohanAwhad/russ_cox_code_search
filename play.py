import json
import os
import sys
import subprocess
import threading
import time
from rich.console import Console
from rich.panel import Panel

console = Console()


class CodeSearchClient:

  def __init__(self, project_path: str):
    self.process = None
    self.project_path = project_path
    self.running = False
    self.reader_thread = None

  def start(self) -> bool:
    """Start the code search server process"""
    try:
      console.print(f"[bold blue]Starting code search server for {self.project_path}...[/bold blue]")

      # Start the server process
      self.process = subprocess.Popen([sys.executable, "main.py", self.project_path],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True,
                                      bufsize=0)

      # Start reader thread
      self.reader_thread = threading.Thread(target=self._read_responses)
      self.reader_thread.daemon = True
      self.reader_thread.start()

      # Wait for initialization
      while not self.running:
        time.sleep(1)
      return True
    except Exception as e:
      console.print(f"[bold red]Error starting server: {str(e)}[/bold red]")
      return False

  def _read_responses(self) -> None:
    """Thread function to read and display responses"""
    while self.process:
      try:
        # Read Content-Length header
        header = self.process.stdout.readline().strip()
        if not header:
          continue

        if header.startswith("Content-Length: "):
          content_length = int(header[16:])

          # Read the blank line
          self.process.stdout.readline()

          # Read the content
          content = self.process.stdout.read(content_length)
          response = json.loads(content)
          if 'status' in response.keys() and response['status'] == 'initialized':
            self.running = True

          self._display_response(response)
      except Exception as e:
        if self.running:
          console.print(f"[red]Error reading response: {str(e)}[/red]")

  def _display_response(self, response: dict) -> None:
    """Display the response from the server"""
    if "error" in response:
      console.print(f"[bold red]Error: {response['error']}[/bold red]")
      return

    if "status" in response:
      if response["status"] == "initialized":
        console.print(f"[green]Initialized with {response['files_indexed']} files indexed[/green]")
      elif response["status"] == "shutdown":
        console.print("[green]Server shut down successfully[/green]")
      elif response["status"] == "success" and "matches" in response:
        console.print(
            f"[green]Found {response['total_matches']} matches, showing {response['returned_matches']}:[/green]")

        for i, match in enumerate(response["matches"]):
          file_path = match["file"]
          file_matches = match["matches"]

          if file_matches:
            match_preview = file_matches[0]["context"]
            console.print(
                Panel(f"[bold]{file_path}[/bold] (line {file_matches[0]['line']})\n[dim]{match_preview}[/dim]",
                      title=f"Match {i+1}",
                      border_style="green"))

            if len(file_matches) > 1:
              console.print(f"  [dim]+ {len(file_matches)-1} more matches in this file[/dim]")

        if response["total_matches"] > response["returned_matches"]:
          console.print(
              f"[dim]+ {response['total_matches'] - response['returned_matches']} more matches not shown[/dim]")

  def send_command(self, command: dict) -> None:
    """Send a command to the server"""
    try:
      if not self.process:
        console.print("[bold red]Server not running[/bold red]")
        return

      content = json.dumps(command)
      message = f"Content-Length: {len(content)}\n\n{content}"

      self.process.stdin.write(message)
      self.process.stdin.flush()
    except Exception as e:
      console.print(f"[bold red]Error sending command: {str(e)}[/bold red]")

  def search(self, pattern: str, max_results: int = 20) -> None:
    """Send a search command"""
    self.send_command({"command": "search", "pattern": pattern, "max_results": max_results})

  def shutdown(self) -> None:
    """Shutdown the server"""
    if self.process:
      try:
        self.send_command({"command": "shutdown"})
        # Give time for response
        time.sleep(0.5)
        self.running = False
        # Clean up
        self.process.terminate()
        if self.reader_thread and self.reader_thread.is_alive():
          self.reader_thread.join(timeout=1)
      except Exception as e:
        console.print(f"[red]Error shutting down: {str(e)}[/red]")


def main() -> None:
  if len(sys.argv) != 2:
    console.print("[bold red]Usage: python play.py <project_path>[/bold red]")
    sys.exit(1)

  project_path = os.path.abspath(sys.argv[1])

  if not os.path.isdir(project_path):
    console.print(f"[bold red]Error: {project_path} is not a valid directory[/bold red]")
    sys.exit(1)

  client = CodeSearchClient(project_path)
  if not client.start():
    sys.exit(1)

  try:
    # Run search for demonstration
    query = '''
  minio:
    image: minio/minio
    ports:
      - "8510:9000"
      - "8511:9001"

'''.strip()

    console.print(f"\n[bold cyan]Searching for:\n{query}  ...[/bold cyan]")
    client.search(query)

    # Wait for the results to be displayed
    time.sleep(2)

  except KeyboardInterrupt:
    console.print("\n[bold]Exiting...[/bold]")
  finally:
    console.print("\n[bold]Shutting down server...[/bold]")
    client.shutdown()


if __name__ == "__main__":
  main()
