"""
Generate and print a colored architecture diagram of the Target System (Raspberry Pi)
"""
try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    try:
        from colorama import init, Fore, Back, Style
        init(autoreset=True)
        COLORAMA_AVAILABLE = True
    except ImportError:
        COLORAMA_AVAILABLE = False

def print_diagram_rich():
    """Print diagram using rich library"""
    import sys
    import io
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    console = Console()
    
    # Create main container
    console.print("\n" + "=" * 90, style="bold cyan")
    console.print(" " * 30 + "TARGET SYSTEM (Raspberry Pi)", style="bold cyan")
    console.print("=" * 90 + "\n", style="bold cyan")
    
    # TargetSystem (Main Orchestrator)
    orchestrator_text = Text()
    orchestrator_text.append("TargetSystem (Main Orchestrator)\n", style="bold yellow")
    orchestrator_text.append("  * Component Initialization\n", style="white")
    orchestrator_text.append("  * Lifecycle Management\n", style="white")
    orchestrator_text.append("  * Signal Handling (SIGINT, SIGTERM)", style="white")
    console.print(Panel(orchestrator_text, border_style="yellow", title="[yellow]target_main.py[/yellow]"))
    
    console.print("\n" + "-" * 90 + "\n", style="cyan")
    
    # Communication Layer
    console.print("COMMUNICATION LAYER", style="bold green")
    console.print("-" * 90 + "\n", style="green")
    
    comm_table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
    comm_table.add_column("Component", style="cyan", width=25)
    comm_table.add_column("Port", style="yellow", width=10)
    comm_table.add_column("Description", style="white", width=50)
    
    comm_table.add_row("TCP Command Server", "2222", "Receives commands from host system")
    comm_table.add_row("TCP Data Server", "12345", "Sends periodic data to host")
    comm_table.add_row("UDP Status Sender", "8888", "Broadcasts status updates")
    comm_table.add_row("UDP Status Receiver", "8889", "Receives status requests")
    
    console.print(comm_table)
    console.print()
    
    # Processing Layer
    console.print("PROCESSING LAYER", style="bold magenta")
    console.print("-" * 90 + "\n", style="magenta")
    
    proc_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    proc_table.add_column("Component", style="cyan", width=30)
    proc_table.add_column("Functionality", style="white", width=55)
    
    proc_table.add_row("Command Processor", "Parses and routes commands to hardware handlers")
    proc_table.add_row("Data Callback Handler", "Manages periodic data collection and transmission")
    
    console.print(proc_table)
    console.print()
    
    # Hardware Abstraction Layer
    console.print("HARDWARE ABSTRACTION LAYER", style="bold blue")
    console.print("-" * 90 + "\n", style="blue")
    
    hal_table = Table(show_header=True, header_style="bold blue", box=box.ROUNDED)
    hal_table.add_column("Component", style="cyan", width=25)
    hal_table.add_column("Interface", style="yellow", width=20)
    hal_table.add_column("Functionality", style="white", width=40)
    
    hal_table.add_row("GPIO Handler", "RPi.GPIO", "Digital I/O control")
    hal_table.add_row("ADC Interface", "MCP3008", "Analog-to-digital conversion")
    
    console.print(hal_table)
    console.print()
    
    # Hardware Layer
    console.print("HARDWARE LAYER", style="bold red")
    console.print("-" * 90 + "\n", style="red")
    
    hw_table = Table(show_header=True, header_style="bold red", box=box.ROUNDED)
    hw_table.add_column("Component", style="cyan", width=30)
    hw_table.add_column("Specifications", style="white", width=55)
    
    hw_table.add_row("GPIO Pins", "LED Pin: 26 (Output), Input Pin: 6 (Input with PUD_DOWN)")
    hw_table.add_row("MCP3008 ADC Chip", "8-channel, 10-bit ADC via SPI interface")
    
    console.print(hw_table)
    console.print()
    
    # Connection flow
    console.print("DATA FLOW", style="bold white on blue")
    console.print("-" * 90 + "\n", style="white")
    
    flow_text = Text()
    flow_text.append("Host System", style="bold white")
    flow_text.append(" -> ", style="yellow")
    flow_text.append("TCP Command Server (2222)", style="green")
    flow_text.append(" -> ", style="yellow")
    flow_text.append("Command Processor", style="magenta")
    flow_text.append(" -> ", style="yellow")
    flow_text.append("GPIO Handler / ADC Interface", style="blue")
    flow_text.append(" -> ", style="yellow")
    flow_text.append("Hardware", style="red")
    
    console.print(flow_text)
    console.print()
    
    flow_text2 = Text()
    flow_text2.append("Hardware", style="red")
    flow_text2.append(" -> ", style="yellow")
    flow_text2.append("ADC Interface / GPIO Handler", style="blue")
    flow_text2.append(" -> ", style="yellow")
    flow_text2.append("Data Callback Handler", style="magenta")
    flow_text2.append(" -> ", style="yellow")
    flow_text2.append("TCP Data Server (12345) / UDP Status Sender (8888)", style="green")
    flow_text2.append(" -> ", style="yellow")
    flow_text2.append("Host System", style="bold white")
    
    console.print(flow_text2)
    console.print()
    
    console.print("=" * 90, style="bold cyan")
    console.print()

def print_diagram_colorama():
    """Print diagram using colorama library"""
    print("\n" + "=" * 90)
    print(Fore.CYAN + Style.BRIGHT + " " * 30 + "TARGET SYSTEM (Raspberry Pi)")
    print("=" * 90 + "\n")
    
    # TargetSystem
    print(Fore.YELLOW + Style.BRIGHT + "+" + "-" * 88 + "+")
    print(Fore.YELLOW + Style.BRIGHT + "|" + " " * 30 + "TargetSystem (Main Orchestrator)" + " " * 30 + "|")
    print(Fore.YELLOW + Style.BRIGHT + "|" + " " * 88 + "|")
    print(Fore.YELLOW + Style.BRIGHT + "|" + Fore.WHITE + "  * Component Initialization" + " " * 60 + Fore.YELLOW + "|")
    print(Fore.YELLOW + Style.BRIGHT + "|" + Fore.WHITE + "  * Lifecycle Management" + " " * 65 + Fore.YELLOW + "|")
    print(Fore.YELLOW + Style.BRIGHT + "|" + Fore.WHITE + "  * Signal Handling (SIGINT, SIGTERM)" + " " * 50 + Fore.YELLOW + "|")
    print(Fore.YELLOW + Style.BRIGHT + "+" + "-" * 88 + "+")
    print(Fore.CYAN + Style.BRIGHT + "\n" + "-" * 90 + "\n")
    
    # Communication Layer
    print(Fore.GREEN + Style.BRIGHT + "COMMUNICATION LAYER")
    print(Fore.GREEN + "-" * 90 + "\n")
    print(Fore.CYAN + "TCP Command Server" + Fore.YELLOW + " (Port 2222)" + Fore.WHITE + " - Receives commands from host system")
    print(Fore.CYAN + "TCP Data Server" + Fore.YELLOW + " (Port 12345)" + Fore.WHITE + " - Sends periodic data to host")
    print(Fore.CYAN + "UDP Status Sender" + Fore.YELLOW + " (Port 8888)" + Fore.WHITE + " - Broadcasts status updates")
    print(Fore.CYAN + "UDP Status Receiver" + Fore.YELLOW + " (Port 8889)" + Fore.WHITE + " - Receives status requests")
    print()
    
    # Processing Layer
    print(Fore.MAGENTA + Style.BRIGHT + "PROCESSING LAYER")
    print(Fore.MAGENTA + "-" * 90 + "\n")
    print(Fore.CYAN + "Command Processor" + Fore.WHITE + " - Parses and routes commands to hardware handlers")
    print(Fore.CYAN + "Data Callback Handler" + Fore.WHITE + " - Manages periodic data collection and transmission")
    print()
    
    # Hardware Abstraction Layer
    print(Fore.BLUE + Style.BRIGHT + "HARDWARE ABSTRACTION LAYER")
    print(Fore.BLUE + "-" * 90 + "\n")
    print(Fore.CYAN + "GPIO Handler" + Fore.YELLOW + " (RPi.GPIO)" + Fore.WHITE + " - Digital I/O control")
    print(Fore.CYAN + "ADC Interface" + Fore.YELLOW + " (MCP3008)" + Fore.WHITE + " - Analog-to-digital conversion")
    print()
    
    # Hardware Layer
    print(Fore.RED + Style.BRIGHT + "HARDWARE LAYER")
    print(Fore.RED + "-" * 90 + "\n")
    print(Fore.CYAN + "GPIO Pins" + Fore.WHITE + " - LED Pin: 26 (Output), Input Pin: 6 (Input with PUD_DOWN)")
    print(Fore.CYAN + "MCP3008 ADC Chip" + Fore.WHITE + " - 8-channel, 10-bit ADC via SPI interface")
    print()
    
    # Data Flow
    print(Fore.WHITE + Style.BRIGHT + Back.BLUE + "DATA FLOW")
    print(Fore.RED + "-" * 90 + "\n")
    print(Fore.WHITE + Style.BRIGHT + "Host System" + Fore.YELLOW + " -> " + 
          Fore.GREEN + "TCP Command Server (2222)" + Fore.YELLOW + " -> " + 
          Fore.MAGENTA + "Command Processor" + Fore.YELLOW + " -> " + 
          Fore.BLUE + "GPIO Handler / ADC Interface" + Fore.YELLOW + " -> " + 
          Fore.RED + "Hardware")
    print()
    print(Fore.RED + "Hardware" + Fore.YELLOW + " -> " + 
          Fore.BLUE + "ADC Interface / GPIO Handler" + Fore.YELLOW + " -> " + 
          Fore.MAGENTA + "Data Callback Handler" + Fore.YELLOW + " -> " + 
          Fore.GREEN + "TCP Data Server (12345) / UDP Status Sender (8888)" + Fore.YELLOW + " -> " + 
          Fore.WHITE + Style.BRIGHT + "Host System")
    print()
    print("=" * 90)

def print_diagram_plain():
    """Print diagram in plain text"""
    print("\n" + "=" * 90)
    print(" " * 30 + "TARGET SYSTEM (Raspberry Pi)")
    print("=" * 90 + "\n")
    
    print("+" + "-" * 88 + "+")
    print("|" + " " * 30 + "TargetSystem (Main Orchestrator)" + " " * 30 + "|")
    print("|" + " " * 88 + "|")
    print("|  * Component Initialization" + " " * 60 + "|")
    print("|  * Lifecycle Management" + " " * 65 + "|")
    print("|  * Signal Handling (SIGINT, SIGTERM)" + " " * 50 + "|")
    print("+" + "-" * 88 + "+")
    print("\n" + "-" * 90 + "\n")
    
    print("COMMUNICATION LAYER")
    print("-" * 90 + "\n")
    print("TCP Command Server (Port 2222) - Receives commands from host system")
    print("TCP Data Server (Port 12345) - Sends periodic data to host")
    print("UDP Status Sender (Port 8888) - Broadcasts status updates")
    print("UDP Status Receiver (Port 8889) - Receives status requests")
    print()
    
    print("PROCESSING LAYER")
    print("-" * 90 + "\n")
    print("Command Processor - Parses and routes commands to hardware handlers")
    print("Data Callback Handler - Manages periodic data collection and transmission")
    print()
    
    print("HARDWARE ABSTRACTION LAYER")
    print("-" * 90 + "\n")
    print("GPIO Handler (RPi.GPIO) - Digital I/O control")
    print("ADC Interface (MCP3008) - Analog-to-digital conversion")
    print()
    
    print("HARDWARE LAYER")
    print("-" * 90 + "\n")
    print("GPIO Pins - LED Pin: 26 (Output), Input Pin: 6 (Input with PUD_DOWN)")
    print("MCP3008 ADC Chip - 8-channel, 10-bit ADC via SPI interface")
    print()
    
    print("DATA FLOW")
    print("-" * 90 + "\n")
    print("Host System -> TCP Command Server (2222) -> Command Processor -> GPIO Handler / ADC Interface -> Hardware")
    print("Hardware -> ADC Interface / GPIO Handler -> Data Callback Handler -> TCP Data Server (12345) / UDP Status Sender (8888) -> Host System")
    print()
    print("=" * 90)

def main():
    """Main function to print the diagram"""
    if RICH_AVAILABLE:
        print_diagram_rich()
    elif COLORAMA_AVAILABLE:
        print_diagram_colorama()
    else:
        print_diagram_plain()
        print("\n" + "=" * 90)
        print("NOTE: For colored output, install 'rich' or 'colorama':")
        print("  pip install rich")
        print("  or")
        print("  pip install colorama")
        print("=" * 90)

if __name__ == "__main__":
    main()

