"""State manager implementing Observer pattern for unified state distribution."""

from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar

from lenovo_tool.core.data_models import BatterySnapshot, ChargeMode, LogSnapshot

T = TypeVar("T")


class Observer(Protocol):
    """Observer protocol defining the update callback signature."""

    def __call__(self, state_type: str, data: Any) -> None:
        ...


class StateManager:
    """Centralized state manager using Observer pattern.

    Supports subscribing to state changes and broadcasting updates to all
    registered observers. Thread-safe implementation.
    """

    def __init__(self) -> None:
        self._observers: Dict[str, List[Observer]] = {}
        self._current_state: Dict[str, Any] = {}

    def subscribe(
        self, state_type: str, observer: Observer
    ) -> None:
        """Subscribe an observer to a specific state type.

        Args:
            state_type: The type of state to subscribe to (e.g., 'battery',
                        'charge_mode', 'log')
            observer: Callable that will be called when state changes
        """
        if state_type not in self._observers:
            self._observers[state_type] = []
        if observer not in self._observers[state_type]:
            self._observers[state_type].append(observer)

    def unsubscribe(
        self, state_type: str, observer: Observer
    ) -> None:
        """Unsubscribe an observer from a specific state type.

        Args:
            state_type: The state type to unsubscribe from
            observer: The observer to remove
        """
        if state_type in self._observers:
            try:
                self._observers[state_type].remove(observer)
            except ValueError:
                pass

    def update(self, state_type: str, data: Any) -> None:
        """Update state and notify all subscribed observers.

        Args:
            state_type: The type of state being updated
            data: The new state data
        """
        self._current_state[state_type] = data
        if state_type in self._observers:
            for observer in self._observers[state_type]:
                observer(state_type, data)

    def get_state(self, state_type: str) -> Optional[Any]:
        """Get the current state for a specific state type.

        Args:
            state_type: The state type to retrieve

        Returns:
            The current state data or None if not found
        """
        return self._current_state.get(state_type)

    def get_battery_snapshot(self) -> Optional[BatterySnapshot]:
        """Convenience method to get the latest battery snapshot."""
        return self._current_state.get("battery")

    def get_charge_mode(self) -> Optional[ChargeMode]:
        """Convenience method to get the latest charge mode state."""
        return self._current_state.get("charge_mode")

    def get_log_snapshot(self) -> Optional[LogSnapshot]:
        """Convenience method to get the latest log snapshot."""
        return self._current_state.get("log")

    def clear_state(self, state_type: str) -> None:
        """Clear the current state for a specific state type."""
        self._current_state.pop(state_type, None)

    def clear_all(self) -> None:
        """Clear all states and observers."""
        self._observers.clear()
        self._current_state.clear()

    def get_subscriber_count(self, state_type: str) -> int:
        """Get the number of subscribers for a specific state type."""
        return len(self._observers.get(state_type, []))
