import os
import re
import shlex
import shutil
import subprocess
import platform
from pathlib import Path


BLOCKED_COMMANDS = {
    "rm",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "shutdown",
    "reboot",
    "poweroff",
    "dd",
    "mkfs",
    "mount",
    "umount",
    "curl",
    "wget",
    "nc",
    "ncat",
    "openssl",
    "scp",
    "ssh",
}

BLOCKED_PATTERNS = [
    "&&",
    "||",
    ";",
    "|",
    ">>",
    " > ",
    " < ",
    "2>",
    "rm ",
    "sudo ",
    "shutdown",
    "reboot",
    "poweroff",
]


def _is_blocked_command(command: str) -> bool:
    text = (command or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if any(token in lowered for token in BLOCKED_PATTERNS):
        return True
    if lowered.startswith(tuple(f"{name} " for name in BLOCKED_COMMANDS)):
        return True
    try:
        parsed = shlex.split(text)
    except ValueError:
        return True
    if not parsed:
        return True
    if parsed[0].lower() in BLOCKED_COMMANDS:
        return True
    return False


def _run_command(command: str) -> dict:
    if _is_blocked_command(command):
        return {
            "status": "blocked",
            "message": "This command is not allowed in safe local mode.",
            "output": "",
        }

    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        combined = "\n".join(part for part in [stdout, stderr] if part)
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "message": "Command executed locally." if proc.returncode == 0 else "Command returned a non-zero exit code.",
            "output": combined or "Command completed with no output.",
            "code": proc.returncode,
        }
    except FileNotFoundError:
        return {"status": "error", "message": "Command not found on this system.", "output": ""}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out after 15 seconds.", "output": ""}


def _run_command_args(args: list[str]) -> dict:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        combined = "\n".join(part for part in [stdout, stderr] if part)
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "message": "Command executed locally." if proc.returncode == 0 else "Command returned a non-zero exit code.",
            "output": combined or "Command completed with no output.",
            "code": proc.returncode,
        }
    except FileNotFoundError:
        return {"status": "error", "message": "Command not found on this system.", "output": ""}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out after 15 seconds.", "output": ""}


def _read_temperature() -> dict:
    os_name = platform.system().lower()
    if os_name == "linux":
        for candidate in [
            "vcgencmd measure_temp",
            "cat /sys/class/thermal/thermal_zone0/temp",
        ]:
            result = _run_command(candidate)
            if result["status"] == "ok":
                output = result["output"].strip()
                if output.startswith("temp="):
                    value = output.replace("temp=", "").replace("'C", "")
                    return {"status": "ok", "message": "System temperature read successfully.", "output": f"CPU temperature: {value}"}
                if output and output.replace(".", "", 1).isdigit():
                    value = float(output) / 1000.0
                    return {"status": "ok", "message": "System temperature read successfully.", "output": f"CPU temperature: {value:.2f}C"}
    elif os_name == "windows":
        for candidate in [
            "powershell -NoProfile -Command \"Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation | Select-Object -First 1 | ForEach-Object { $_.Temperature }\"",
            "wmic path win32_temperatureprobe get currentreading",
        ]:
            result = _run_command(candidate)
            if result["status"] == "ok":
                output = result["output"].strip()
                cleaned = re.sub(r"[^0-9.\-]", "", output)
                if cleaned:
                    return {"status": "ok", "message": "System temperature read successfully.", "output": f"CPU temperature: {cleaned}C"}
    return {"status": "error", "message": "Could not read system temperature.", "output": ""}


def _read_memory_usage() -> dict:
    os_name = platform.system().lower()
    if os_name == "linux":
        result = _run_command("free -m")
        if result["status"] == "ok":
            return {"status": "ok", "message": "Memory usage fetched.", "output": result["output"]}
        return result
    if os_name == "windows":
        result = _run_command("powershell -NoProfile -Command \"(Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory) | Format-Table -HideTableHeaders\"")
        if result["status"] == "ok":
            return {"status": "ok", "message": "Memory usage fetched.", "output": result["output"]}
        return {"status": "error", "message": "Memory usage command is unavailable on this system.", "output": ""}
    return {"status": "error", "message": "Memory usage command is unavailable on this system.", "output": ""}


def _read_disk_usage() -> dict:
    usage = shutil.disk_usage('.')
    total = usage.total / (1024 ** 3)
    used = usage.used / (1024 ** 3)
    free = usage.free / (1024 ** 3)
    return {
        "status": "ok",
        "message": "Disk usage fetched.",
        "output": f"Disk usage: {used:.2f} GB used / {total:.2f} GB total / {free:.2f} GB free",
    }


def _read_processes() -> dict:
    os_name = platform.system().lower()
    if os_name == "windows":
        result = _run_command("tasklist")
        if result["status"] == "ok":
            return {"status": "ok", "message": "Running processes fetched.", "output": result["output"]}
        return result
    result = _run_command("ps -eo pid,comm,%cpu,%mem --sort=-%cpu")
    if result["status"] == "ok":
        return {"status": "ok", "message": "Running processes fetched.", "output": result["output"]}
    return result


def _read_top_processes(limit: int = 5) -> dict:
    safe_limit = max(1, min(int(limit), 20))
    os_name = platform.system().lower()
    if os_name == "windows":
        powershell = shutil.which("powershell") or shutil.which("powershell.exe")
        if powershell:
            result = _run_command_args([powershell, "-NoProfile", "-Command", "Get-Process | Sort-Object CPU -Descending"])
            header_lines = 3
        else:
            result = _run_command_args(["tasklist"])
            header_lines = 3
        if result["status"] == "ok":
            lines = [line for line in result["output"].splitlines() if line.strip()]
            entries = lines[header_lines:header_lines + safe_limit] if len(lines) > header_lines else lines
            return {"status": "ok", "message": f"Top {safe_limit} running processes fetched.", "output": "\n".join(entries)}
        return result

    result = _run_command_args(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"])
    if result["status"] == "ok":
        lines = [line for line in result["output"].splitlines() if line.strip()]
        trimmed = lines[1:1 + safe_limit] if len(lines) > 1 else lines
        return {"status": "ok", "message": f"Top {safe_limit} running processes fetched.", "output": "\n".join(trimmed)}
    return result


def _run_grep_query(term: str, file_path: str) -> dict:
    safe_term = (term or "").strip()
    safe_path = (file_path or "").strip()
    if not safe_term or not safe_path:
        return {"status": "blocked", "message": "A grep query requires both a search term and a file path.", "output": ""}
    if any(token in safe_path for token in ["&&", "||", ";", "|", ">", "<"]):
        return {"status": "blocked", "message": "This grep pattern is not allowed in safe local mode.", "output": ""}
    return _run_command_args(["grep", "-n", safe_term, safe_path])


def _search_files(term: str, root: str = ".") -> dict:
    search_term = (term or "").strip().strip("\"'")
    if not search_term:
        return {"status": "error", "message": "A file search requires a word or phrase.", "output": ""}

    ignored = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache"}
    matches = []
    scanned = 0
    try:
        for path in Path(root).rglob("*"):
            if any(part in ignored for part in path.parts) or not path.is_file():
                continue
            try:
                if path.stat().st_size > 10 * 1024 * 1024:
                    continue
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if search_term.lower() in line.lower():
                            matches.append(f"{path}:{line_number}: {line.strip()[:240]}")
                            if len(matches) >= 25:
                                break
                scanned += 1
            except (OSError, UnicodeError):
                continue
            if len(matches) >= 25:
                break
    except OSError as error:
        return {"status": "error", "message": f"File search failed: {error}", "output": ""}

    if matches:
        return {
            "status": "ok",
            "message": f"Found {len(matches)} matching line(s) while searching {scanned} file(s).",
            "output": "\n".join(matches),
        }
    return {
        "status": "ok",
        "message": f"No files containing '{search_term}' were found after searching {scanned} file(s).",
        "output": "No matching files found.",
    }


def _build_grep_command(query: str, file_path: str) -> str:
    term = (query or "").strip()
    target = (file_path or "").strip()
    if not term or not target:
        return ""
    safe_term = shlex.quote(term)
    safe_path = shlex.quote(target)
    return f"grep -n {safe_term} {safe_path}"


def detect_local_command_query(query: str) -> str | None:
    text = (query or "").strip()
    if not text:
        return None
    lower = text.lower()

    top_match = re.search(r"(?:show|display|list|check)\s+(?:for\s+)?(?:the\s+)?top\s+(\d+)\s+(?:running\s+)?process(?:es)?", lower)
    if top_match:
        return f"top_processes:{top_match.group(1)}"

    if re.search(r"(?:show|display|list|check)\s+(?:for\s+)?(?:the\s+)?top\s+running\s+processes", lower) or "top processes" in lower:
        return "top_processes:5"

    grep_match = re.search(
        r"(?:grep|search)\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s+(?:in\s+)?(.+)",
        text,
        flags=re.IGNORECASE,
    )
    if grep_match:
        term = grep_match.group(1) or grep_match.group(2) or grep_match.group(3)
        file_path = grep_match.group(4).strip()
        if term and file_path:
            safe = _build_grep_command(term, file_path)
            if safe:
                return safe

    file_search_match = re.search(
        r"(?:check|find|search|look\s+for).*?\bfile(?:s)?\b.*?\b(?:word|words|text|containing)\b\s*[:,]?\s*[\"']([^\"']+)[\"']",
        text,
        flags=re.IGNORECASE,
    )
    if file_search_match:
        term = file_search_match.group(1).strip()
        if term:
            return f"search_files:{term}"

    if "check my temperature" in lower or "cpu temp" in lower or "pi temp" in lower or "system temperature" in lower:
        return "temperature"
    if "check memory usage" in lower or "memory usage" in lower or "free -m" in lower:
        return "memory"
    if "check disk space" in lower or "disk space" in lower or "df -h" in lower:
        return "disk"
    if "show running processes" in lower or "running processes" in lower or "ps -eo" in lower:
        return "processes"

    if re.search(r"\b(run|execute|start|check|show|list)\b", lower):
        command_match = re.search(r"\b(?:run|execute|start|check|show|list)\b\s+(.*)$", text, flags=re.IGNORECASE)
        if command_match:
            candidate = command_match.group(1).strip()
            if candidate:
                return candidate

    if re.match(r"^[a-zA-Z0-9_./\-\s]+$", text) and " " not in text:
        return text
    if re.match(r"^(ls|pwd|whoami|git status|git log|python --version|df -h|free -m|ps -eo)[\s\S]*$", text):
        return text

    return None


def execute_local_command(query: str) -> dict:
    command = detect_local_command_query(query)
    if command is None:
        return {"status": "not_found", "message": "No safe local command matched this request.", "output": ""}

    if command.startswith("top_processes:"):
        limit = int(command.split(":", 1)[1])
        return _read_top_processes(limit)

    if command.startswith("search_files:"):
        return _search_files(command.split(":", 1)[1])

    if command.startswith("grep -n "):
        parsed = shlex.split(command)
        if len(parsed) >= 4 and parsed[0].lower() == "grep":
            return _run_grep_query(parsed[2], parsed[3])
        return {"status": "error", "message": "Unable to grep the requested file.", "output": ""}

    if command == "temperature":
        return _read_temperature()

    if command == "memory":
        return _read_memory_usage()

    if command == "disk":
        return _read_disk_usage()

    if command == "processes":
        return _read_processes()

    result = _run_command(command)
    if result["status"] in {"ok", "error", "blocked"}:
        return result
    return {"status": "error", "message": "Unable to execute command.", "output": ""}
