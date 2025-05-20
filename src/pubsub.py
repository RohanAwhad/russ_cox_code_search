from collections import defaultdict
from typing import Callable, Any

class PubSub:
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[str, Any], None]) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: Any) -> None:
        for callback in self._subscribers[event_type]:
            callback(event_type, data)
