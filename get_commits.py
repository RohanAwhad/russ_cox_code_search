#!/usr/bin/env python3

# /// script
# dependencies = [
#   "rich",
#   "typer",
# ]
# ///

import os
import subprocess
import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()

def get_last_n_commits_diffs(n: int = 2):
    """Get the diffs for the last n commits."""
    try:
        # Get the last n commit hashes
        commit_hashes_output = subprocess.check_output(
            ["git", "log", f"-{n}", "--pretty=format:%H"],
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip().split('\n')
        
        diffs = []
        
        # For each commit, get its diff
        for commit_hash in commit_hashes_output:
            # Get the diff for this specific commit
            diff_output = subprocess.check_output(
                ["git", "show", commit_hash],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            
            # Get commit message for this commit
            commit_msg = subprocess.check_output(
                ["git", "log", "-1", "--pretty=format:%s", commit_hash],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            
            diffs.append({
                "hash": commit_hash,
                "message": commit_msg,
                "diff": diff_output
            })
        
        return diffs
    
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error executing git command:[/bold red] {e.output.decode('utf-8')}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

def main(
    num_commits: int = typer.Option(2, "--num-commits", "-n", help="Number of commits to show diffs for"),
):
    """
    Show diffs for recent Git commits.
    """
    try:
        # Check if the current directory is a git repository
        if not os.path.exists('.git'):
            console.print("[bold red]Error:[/bold red] Not a git repository (or any of the parent directories)")
            raise typer.Exit(code=1)
        
        diffs = get_last_n_commits_diffs(num_commits)
        
        for i, diff_info in enumerate(diffs):
            commit_hash = diff_info["hash"]
            commit_msg = diff_info["message"]
            diff_content = diff_info["diff"]
            
            console.print(f"\n[bold green]Commit {commit_hash[:8]}[/bold green] - {commit_msg}")
            syntax = Syntax(diff_content, "diff", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, expand=False))
            
            if i < len(diffs) - 1:
                console.print("\n" + "-" * 80)
                
    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    typer.run(main)
