import os
import wikipediaapi

DATA_DIR = "./my_source_files"
os.makedirs(DATA_DIR, exist_ok=True)

wiki_bot = wikipediaapi.Wikipedia(
    user_agent="Local-Pi-Assistant/1.0 (contact: johnguys1000@egmail.com)",
    language="en",
    extract_format=wikipediaapi.ExtractFormat.WIKI
)

topics_to_download = [
    # Linux — Core
    "Linux", "Linux kernel", "Linux distribution", "GNU", "GNU/Linux",
    "Free and open-source software", "Open-source software", "Unix", "Unix-like", "POSIX",
    "Linux Standard Base", "Linux distributions", "Arch Linux", "Debian", "Ubuntu",
    "Fedora Linux", "Red Hat Enterprise Linux", "CentOS", "openSUSE", "Alpine Linux",
    "Gentoo Linux", "Linux Mint", "Manjaro", "Kali Linux", "Tails (operating system)",
    "NixOS", "Void Linux", "Slackware",

    # Linux — History & People
    "Linus Torvalds", "Richard Stallman", "Dennis Ritchie", "Ken Thompson", "Brian Kernighan",
    "Andrew S. Tanenbaum", "GNU Project", "Free Software Foundation", "Linux Foundation",
    "History of Linux", "History of Unix", "History of computing", "Unix philosophy",

    # Linux — Filesystems & Storage
    "Filesystem", "File system hierarchy", "Filesystem Hierarchy Standard", "ext4", "ext3",
    "ext2", "Btrfs", "XFS", "ZFS", "F2FS",
    "tmpfs", "procfs", "sysfs", "devfs", "Virtual file system",
    "Inode", "File descriptor", "Symbolic link", "Hard link", "Mount (computing)",
    "Disk partitioning", "Logical Volume Management", "LVM", "RAID",

    # Linux — Shell & Processes
    "Bash (Unix shell)", "Z shell", "Fish (Unix shell)", "Shell (computing)",
    "Command-line interface", "Terminal emulator", "TTY", "Pseudoterminal",
    "GNU Core Utilities", "GNU Bash",
    "stdin", "stdout", "stderr", "Pipeline (Unix)", "Redirection (computing)",
    "Shell script", "Environment variable", "Cron", "systemd", "Daemon (computing)",
    "Process (computing)", "Thread (computing)", "Job control (Unix)",
    "Signals (IPC)", "Inter-process communication",

    # Linux — Commands & Utilities
    "ls (Unix)", "cd (command)", "pwd (Unix)", "cp (Unix)", "mv (Unix)",
    "rm (Unix)", "mkdir", "rmdir", "touch (Unix)", "cat (Unix)",
    "less (Unix)", "more (Unix)", "head (Unix)", "tail (Unix)", "grep",
    "sed", "awk", "find (Unix)", "xargs", "sort (Unix)",
    "uniq", "cut (Unix)", "tr (Unix)", "diff", "patch (Unix)",
    "tee (command)", "echo (command)", "printf (Unix)", "man page", "info (Unix)",
    "apropos", "which (command)", "whereis", "locate (Unix)", "file (command)",
    "stat (system call)", "du (Unix)", "df (Unix)", "free (Unix)", "top (software)",
    "htop", "ps (Unix)", "kill (command)", "pkill", "pgrep",
    "nice (Unix)", "renice", "nohup", "watch (Unix)", "uptime",
    "uname", "dmesg", "journalctl", "systemctl",

    # Linux — Package Management
    "Package manager", "Software package", "Pacman (package manager)",
    "Arch User Repository", "AUR helper", "APT (software)", "dpkg",
    "Snap (software)", "Flatpak", "AppImage",
    "DNF (software)", "RPM Package Manager", "YUM", "Portage (software)",
    "Homebrew (package manager)", "Nix package manager", "Nixpkgs",
    "Build system", "Make (software)", "CMake", "Meson (software)",
    "Ninja (build system)", "Autotools",

    # Linux — Security
    "Linux security", "Unix security", "User account", "Root user", "Superuser",
    "sudo", "su (Unix)", "File-system permissions", "chmod", "chown",
    "setuid", "setgid", "Access control list", "POSIX ACL", "SELinux",
    "AppArmor", "Linux namespaces", "Control groups", "seccomp", "Linux capabilities",
    "Linux kernel security", "Secure Boot", "Trusted Platform Module",
    "Disk encryption", "LUKS", "Cryptsetup", "GPG", "OpenSSH",
    "SSH", "Firewall", "iptables", "nftables", "UFW",
    "Fail2ban", "Auditd", "Linux audit framework",

    # Cybersecurity — Fundamentals
    "Cybersecurity", "Information security", "Computer security", "Network security",
    "Application security", "Cloud security", "Endpoint security",
    "Security engineering", "Cryptography", "Authentication",
    "Authorization", "Access control", "Multi-factor authentication",
    "Identity management", "Zero trust security model", "Defense in depth",
    "Principle of least privilege", "Security information and event management",
    "Intrusion detection system", "Intrusion prevention system",
    "Security vulnerability", "Common Vulnerabilities and Exposures",
    "Common Weakness Enumeration", "CVSS", "Exploit",

    # Cybersecurity — Threats & Attacks
    "Malware", "Computer virus", "Computer worm", "Trojan horse", "Ransomware",
    "Rootkit", "Spyware", "Botnet", "Phishing", "Social engineering (security)",
    "Denial-of-service attack", "Distributed denial-of-service attack",
    "Man-in-the-middle attack", "Replay attack", "Brute-force attack",
    "Credential stuffing", "Password cracking", "Security incident",
    "Incident response", "Digital forensics", "Computer forensics",
    "Threat intelligence", "Threat modeling", "Penetration test",
    "Vulnerability assessment", "Security audit",

    # Networking — Fundamentals
    "Computer network", "Computer networking", "Internet", "Internet protocol suite",
    "OSI model", "TCP/IP", "Ethernet", "MAC address", "IP address",
    "IPv4", "IPv6", "Subnet", "Subnetting", "CIDR",
    "Routing", "Router", "Switch (networking)", "Network bridge",
    "Network interface controller", "Network topology",

    # Networking — Protocols
    "Domain Name System", "DNS", "DHCP", "ARP", "ICMP",
    "TCP", "UDP", "QUIC", "HTTP", "HTTPS",
    "FTP", "SFTP", "SSH", "SMTP", "IMAP",
    "POP3", "SNMP", "NTP", "VPN", "WireGuard",
    "OpenVPN", "Proxy server", "Reverse proxy", "Network address translation",
    "Port forwarding", "Firewall (computing)", "Packet analyzer",
    "Wireshark", "Network monitoring",

    # Programming — Languages
    "Programming language", "History of programming languages",
    "Machine code", "Assembly language", "C (programming language)", "C++",
    "C Sharp (programming language)", "Rust (programming language)",
    "Go (programming language)", "Java (programming language)",
    "JavaScript", "TypeScript", "Python (programming language)",
    "Ruby (programming language)", "PHP", "Perl",
    "Lua (programming language)", "Kotlin", "Swift (programming language)",
    "Dart (programming language)", "R (programming language)", "MATLAB",
    "Scala (programming language)", "Haskell", "Erlang",
    "Elixir (programming language)", "OCaml", "Fortran", "COBOL",
    "Pascal (programming language)", "Ada (programming language)",
    "Objective-C", "Visual Basic", "BASIC", "SQL", "WebAssembly",

    # Programming — Concepts
    "Algorithm", "Data structure", "Array data structure", "Linked list",
    "Stack (abstract data type)", "Queue (abstract data type)", "Hash table",
    "Tree (data structure)", "Graph (abstract data type)", "Binary search tree",
    "Sorting algorithm", "Search algorithm", "Recursion", "Object-oriented programming",
    "Functional programming", "Procedural programming", "Imperative programming",
    "Declarative programming", "Generic programming", "Metaprogramming",
    "Design pattern (computer science)", "Software architecture", "Compiler",
    "Interpreter (computing)", "Just-in-time compilation", "Static analysis",
    "Dynamic analysis", "Garbage collection (computer science)", "Memory management",
    "Pointer (computer programming)", "Reference (computer science)",
    "Concurrency (computer science)", "Parallel computing", "Multithreading",
    "Asynchronous programming", "Exception handling", "Debugging",
    "Unit testing", "Integration testing", "Software testing",

    # Compilers & Development Tools
    "Compiler construction", "GNU Compiler Collection", "Clang", "LLVM", "GDB (debugger)",
    "Valgrind", "GNU Binutils", "Linker (computing)", "Object file", "Executable",
    "ELF (file format)", "Dynamic-link library", "Shared library", "Static library",
    "Application programming interface", "ABI", "SDK", "IDE", "Text editor",
    "Visual Studio Code", "Vim", "Neovim", "Emacs",

    # Version Control & DevOps
    "Git", "GitHub", "GitLab", "Bitbucket", "Version control",
    "Distributed version control", "Continuous integration", "Continuous delivery",
    "DevOps", "DevSecOps", "CI/CD", "Docker", "Containerization",
    "Kubernetes", "Podman", "Virtual machine", "Hypervisor", "QEMU",
    "VirtualBox", "VMware", "Infrastructure as code", "Terraform", "Ansible",

    # Windows — Core
    "Microsoft Windows", "Windows NT", "Windows 10", "Windows 11", "Windows Server",
    "Windows kernel", "Windows architecture", "Windows Registry", "Windows API",
    "Win32", "PowerShell", "Command Prompt", "Windows Subsystem for Linux",
    "Windows Terminal", "NTFS", "FAT32", "exFAT", "BitLocker",
    "Windows Defender", "Microsoft Defender Antivirus", "Windows Firewall",
    "Windows Update", "Windows services", "Windows Task Manager",
    "Windows Device Manager", "Active Directory", "Group Policy",
    "Remote Desktop Protocol", "SMB protocol", "Windows Event Log",
    "Event Viewer", "Windows Security", "Windows authentication",
    "Kerberos", "NTLM", "DLL", "EXE", "Portable Executable",
    "Windows boot process", "Boot Configuration Data", "Windows Recovery Environment",

    # Microsoft
    "Microsoft", "History of Microsoft", "Bill Gates", "Paul Allen",
    "Satya Nadella", "Microsoft Azure", "Microsoft 365", "Microsoft Office",
    "Microsoft Visual Studio", ".NET", ".NET Framework", "ASP.NET",
    "C Sharp (programming language)", "TypeScript", "GitHub", "Xbox",
    "DirectX", "Microsoft SQL Server", "Microsoft Edge",

    # Databases
    "Database", "Database management system", "Relational database", "NoSQL",
    "SQL", "MySQL", "PostgreSQL", "SQLite", "MariaDB",
    "MongoDB", "Redis", "Oracle Database", "Microsoft SQL Server",
    "Database normalization", "Transaction processing", "ACID",
    "Database index", "Structured Query Language",

    # Web Development
    "World Wide Web", "Web development", "Web application", "Web server",
    "Apache HTTP Server", "NGINX", "Node.js", "Deno", "Bun (software)",
    "HTML", "CSS", "JavaScript", "TypeScript", "React (JavaScript library)",
    "Angular (web framework)", "Vue.js", "Svelte", "Next.js",
    "REST", "RESTful API", "GraphQL", "WebSocket", "JSON",
    "XML", "Cookie (computing)", "HTTP cookie",
    "Cross-site scripting", "SQL injection", "Cross-site request forgery",
    "Content Security Policy",

    # Hardware & Computer Systems
    "Computer architecture", "Computer organization", "Central processing unit",
    "Microprocessor", "Graphics processing unit", "Memory hierarchy",
    "Random-access memory", "Cache (computing)", "Virtual memory",
    "Motherboard", "BIOS", "UEFI", "Booting", "Firmware",
    "Device driver", "Peripheral", "USB", "PCI Express", "SATA",
    "NVMe", "SSD", "Hard disk drive", "ARM architecture family",
    "x86", "x86-64", "RISC-V", "Embedded system",
    "Microcontroller", "Raspberry Pi", "Arduino", "ESP32",

    # Operating System Theory
    "Operating system", "Operating system theory", "Kernel (operating system)",
    "Monolithic kernel", "Microkernel", "Hybrid kernel", "Process management",
    "Memory management", "Virtual memory", "Scheduling (computing)",
    "Process scheduling", "Deadlock (computer science)", "File system",
    "Device driver", "System call", "Interrupt", "Context switch",
    "User space", "Kernel space", "Privilege ring",
    "Inter-process communication", "Operating system security",

    # Other Operating Systems
    "Android (operating system)", "Android kernel", "ChromeOS", "macOS",
    "iOS", "iPadOS", "FreeBSD", "OpenBSD", "NetBSD",
    "DragonFly BSD", "Solaris (operating system)", "Darwin (operating system)",
    "Haiku (operating system)", "ReactOS", "DOS", "MS-DOS",
    "OS/2", "Unix",

    # Cloud & Servers
    "Cloud computing", "Cloud computing security", "Amazon Web Services",
    "Microsoft Azure", "Google Cloud Platform", "Cloud storage",
    "Virtual private server", "Server (computing)", "Web server",
    "File server", "DNS server", "Database server", "Mail server",
    "Proxy server", "Load balancing", "High availability", "Fault tolerance",

    # Cybersecurity Tools
    "Kali Linux", "Parrot OS", "Aircrack-ng", "Nmap", "Metasploit",
    "Burp Suite", "Wireshark", "tcpdump", "John the Ripper", "Hashcat",
    "Nikto", "OpenVAS", "Nessus", "OWASP", "OWASP Top Ten",
    "Security Onion",

    # Digital Forensics
    "Digital forensics", "Computer forensics", "Network forensics",
    "Memory forensics", "Disk image", "File carving", "Digital evidence",
    "Chain of custody", "Volatility (memory forensics)", "Autopsy (software)",
    "The Sleuth Kit",

    # Cryptography
    "Cryptography", "Cryptanalysis", "Encryption", "Decryption",
    "Advanced Encryption Standard", "RSA (cryptosystem)",
    "Diffie–Hellman key exchange", "Elliptic-curve cryptography",
    "SHA-2", "SHA-3", "MD5", "Secure Hash Algorithms", "HMAC",
    "Digital signature", "Certificate authority", "TLS", "PGP",
    "GNU Privacy Guard",

    # AI & Machine Learning
    "Artificial intelligence", "Machine learning", "Deep learning",
    "Neural network", "Large language model", "Natural language processing",
    "Computer vision", "TensorFlow", "PyTorch", "scikit-learn",
    "NumPy", "Pandas (software)", "Jupyter",

    # Software Engineering
    "Software engineering", "Software development", "Software development life cycle",
    "Agile software development", "Scrum (software development)",
    "Extreme programming", "Waterfall model", "Requirements engineering",
    "Software architecture", "Microservices", "Monolithic application",
    "API", "Technical debt", "Code review", "Refactoring",
    "Documentation", "Semantic versioning", "Software license",
    "MIT License", "GNU General Public License", "Apache License",
    "Mozilla Public License",

    # Computer Science
    "Computer science", "Computability theory", "Computational complexity theory",
    "Theory of computation", "Automata theory", "Formal language",
    "Compiler theory", "Discrete mathematics", "Boolean algebra", "Logic",
    "Graph theory", "Probability", "Information theory",
    "Information technology", "Distributed computing", "Parallel computing",
    "Computer architecture", "Artificial intelligence",
]

print(f"Starting automated background downloader directly to: {DATA_DIR}\n")

for topic in topics_to_download:
    print(f"Fetching core text for: '{topic}'...")
    page = wiki_bot.page(topic)

    if not page.exists():
        print(f"Could not find an official Wikipedia article for '{topic}'. Skipping.")
        continue

    safe_title = topic.replace(" ", "_").replace("/", "-")
    filename = f"Wikipedia-{safe_title}.txt"
    filepath = os.path.join(DATA_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(page.text)

    print(f"Saved perfectly: {filename}")

print("\nAll text files downloaded cleanly! Run your ingest_bm25.py script now.")