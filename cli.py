import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.prompt import Prompt

from src.agent import VelaAgent

console = Console()

def display_banner():
    banner_text = Text()
    banner_text.append("💜  L U M I  ·  A N T I G R A V I T Y\n", style="bold magenta")
    banner_text.append("Shop smarter. Love what you find.\n", style="italic white")
    banner_text.append("Engineered with LangGraph StateGraph & MemorySaver (No External Tracers Required)", style="dim green")
    
    console.print(Panel(
        banner_text,
        title="[bold magenta]LIVE SHOPPING TERMINAL[/bold magenta]",
        border_style="cyan",
        padding=(1, 2)
    ))

def main():
    display_banner()
    agent = VelaAgent(thread_id="streetwear_session_01")
    
    # Opening greeting
    greeting = agent.start_conversation()
    console.print(Panel(Markdown(greeting), title="[bold magenta]Lumi[/bold magenta]", border_style="magenta"))
    
    while True:
        try:
            user_msg = Prompt.ask("\n[bold yellow]You[/bold yellow]")
            if not user_msg.strip():
                continue
            if user_msg.strip().lower() in ["exit", "quit", "q"]:
                console.print("\n[dim]Session closed. Stay elevated.[/dim]")
                break

            response = agent.chat(user_msg)
            console.print(Panel(
                Markdown(response),
                title="[bold magenta]Lumi[/bold magenta]",
                border_style="magenta"
            ))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session interrupted. Goodbye![/dim]")
            break

if __name__ == "__main__":
    main()
