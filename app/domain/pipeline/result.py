from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PluginResult:
    name: str
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
