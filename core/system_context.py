from datetime import datetime
import os
import platform
from typing import Any, Dict


def _read_temperature() -> float | None:
    if platform.system().lower() != "linux":
        return None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as handle:
            return round(int(handle.read().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def _read_battery() -> Dict[str, Any]:
    power_path = "/sys/class/power_supply"
    try:
        for name in os.listdir(power_path):
            base = os.path.join(power_path, name)
            capacity_path = os.path.join(base, "capacity")
            if os.path.isfile(capacity_path):
                with open(capacity_path, "r", encoding="utf-8") as handle:
                    return {"percent": int(handle.read().strip()), "source": name}
    except (OSError, ValueError):
        pass
    return {"percent": None, "source": "unknown"}


def read_system_context(settings: Dict[str, Any]) -> Dict[str, Any]:
    if settings.get("system_awareness") == "off":
        return {"power_saving_mode": bool(settings.get("power_saving_mode"))}
    context: Dict[str, Any] = {}
    if settings.get("allow_clock"):
        now = datetime.now().astimezone()
        context.update({
            "local_time": now.strftime("%H:%M"),
            "local_date": now.strftime("%Y-%m-%d"),
            "timezone": now.tzname() or "local",
        })
    if settings.get("allow_thermal_status"):
        context["cpu_temperature_c"] = _read_temperature()
    if settings.get("allow_battery_status"):
        context["battery"] = _read_battery()
    context["power_saving_mode"] = bool(settings.get("power_saving_mode"))
    return context