"""Explicit, read-only local tools exposed to the assistant."""

from typing import Any, Dict

from . import local_commands


TOOL_SCHEMAS = {
    "get_temperature": {"description": "Read CPU temperature."},
    "get_memory_usage": {"description": "Read system memory usage."},
    "get_disk_usage": {"description": "Read disk usage for the assistant directory."},
    "get_processes": {"description": "List running processes."},
    "get_top_processes": {"description": "Read the top CPU processes.", "max_limit": 20},
}


def execute_tool(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    arguments = arguments or {}
    if name == "get_temperature":
        return local_commands._read_temperature()
    if name == "get_memory_usage":
        return local_commands._read_memory_usage()
    if name == "get_disk_usage":
        return local_commands._read_disk_usage()
    if name == "get_processes":
        return local_commands._read_processes()
    if name == "get_top_processes":
        limit = max(1, min(int(arguments.get("limit", 5)), 20))
        return local_commands._read_top_processes(limit)
    return {"status": "error", "message": f"Unknown local tool: {name}", "output": ""}
