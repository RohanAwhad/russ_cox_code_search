#!/usr/bin/env python
import json
import subprocess
import sys
from threading import Thread
from typing import Optional, Dict, Any

from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.panel import Panel


class SearchClient:
    def __init__(self, project_path: str):
        self.console = Console()
        self.proc = subprocess.Popen(
            [sys.executable, "main.py", project_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=0
        )
        self.running = True
        Thread(target=self._read_output, daemon=True).start()

    def _read_output(self) -> None:
        while self.running:
            content_length = 0
            while True:
                line = self.proc.stdout.readline().strip()
                if not line:
                    break
                if line.startswith("Content-Length: "):
                    content_length = int(line[16:])

            if content_length > 0:
                content = self.proc.stdout.read(content_length)
                response = json.loads(content)
                self._display_response(response)

    def _display_response(self, response: Dict[str, Any]) -> None:
        if "error" in response:
            self.console.print(f"[bold red]Error: {response['error']}[/]")
            return

        if "results" in response:
            for result in response["results"]:
                docstring = result.get("docstring", "No docstring available")
                self.console.print(
                    Panel.fit(
                        Syntax(docstring, "python", theme="monokai", line_numbers=False),
                        title=f"[bold cyan]{result['filepath']}[/]",
                        title_align="left",
                        border_style="blue"
                    )
                )

    def send_command(self, command: str, params: Dict[str, Any]) -> None:
        message = {"command": command, **params}
        content = json.dumps(message)
        self.proc.stdin.write(f"Content-Length: {len(content)}\n\n{content}")
        self.proc.stdin.flush()

    def shutdown(self) -> None:
        self.running = False
        self.send_command("shutdown", {})
        self.proc.wait()


def main():
    if len(sys.argv) != 2:
        print("Usage: python play.py <project_path>")
        sys.exit(1)

    console = Console()
    client = SearchClient(sys.argv[1])

    try:
        while True:
            query = Prompt.ask("[bold magenta]Enter semantic search query[/] (or 'exit' to quit)")
            if query.lower() == "exit":
                break
            client.send_command("ssearch", {"query": query})
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        client.shutdown()
        console.print("[bold green]Goodbye![/]")


if __name__ == "__main__":
    main()
