import re
import os
import sys

from rich.console import Console
from rich.panel import Panel

from src import indexer

console = Console()


def main():
  if len(sys.argv) != 2:
    console.print("[bold red]Usage: python code_search_cli.py <project_path>[/bold red]")
    sys.exit(1)

  project_path = sys.argv[1]

  if not os.path.isdir(project_path):
    console.print(f"[bold red]Error: {project_path} is not a valid directory[/bold red]")
    sys.exit(1)

  searcher, file_mapping, observer = indexer.index_project(project_path, watch=True)

  while True:
    try:
      console.print("\n[bold]Enter a regex pattern to search (Ctrl+C to exit):[/bold]", end=" ")
      pattern = input()
      # Auto-escape regex special characters if not starting with 'r:'
      if not pattern.startswith('r:'):
        pattern = re.escape(pattern)
      else:
        pattern = pattern[2:]  # Remove the 'r:' prefix

      with console.status("[bold green]Searching...[/bold green]"):
        results = searcher.search(pattern)

      if not results:
        console.print("[yellow]No matches found.[/yellow]")
        continue

      console.print(f"[green]Found {len(results)} matching files. Top results:[/green]")

      for idx, doc_id in enumerate(results[:3]):
        file_path = file_mapping[doc_id]
        try:
          with open(os.path.join(project_path, file_path), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

          # Find the first match in the file
          match = re.search(pattern, content)
          context = ""
          if match:
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = "..." + content[start:end].replace("\n", "\\n") + "..."

          console.print(
              Panel(f"[bold]{file_path}[/bold]\n[dim]{context}[/dim]",
                    title=f"Match {idx+1}",
                    title_align="left",
                    border_style="green"))
        except Exception as e:
          console.print(f"[yellow]Error reading {file_path}: {str(e)}[/yellow]")

    except KeyboardInterrupt:
      console.print("\n[bold]Exiting...[/bold]")
      if observer:
        observer.stop()
        observer.join()
      break
    except Exception as e:
      console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
  main()
