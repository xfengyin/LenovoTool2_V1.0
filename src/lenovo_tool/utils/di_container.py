"""Simple dependency injection container with constructor injection and mocking."""

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class DIContainer:
    """Lightweight dependency injection container.

    Features:
        - Constructor injection based on type hints
        - Singleton management
        - Mock replacement for testing
        - Lazy initialization
    """

    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable[..., Any]] = {}
        self._instances: dict[str, Any] = {}

    def register_factory(self, key: str, factory: Callable[..., Any]) -> None:
        """Register a factory function for a key.

        Args:
            key: Dependency key
            factory: Factory function that creates the instance
        """
        self._factories[key] = factory
        if key in self._singletons:
            del self._singletons[key]

    def register_instance(self, key: str, instance: Any) -> None:
        """Register a singleton instance for a key.

        Args:
            key: Dependency key
            instance: Instance to register
        """
        self._instances[key] = instance
        if key in self._singletons:
            del self._singletons[key]
        if key in self._factories:
            del self._factories[key]

    def resolve(self, key: str, **kwargs: Any) -> Any:
        """Resolve a dependency.

        Args:
            key: Dependency key
            kwargs: Additional arguments to pass to the factory

        Returns:
            Resolved instance

        Raises:
            RuntimeError: If dependency is not registered
        """
        if key in self._instances:
            return self._instances[key]

        if key in self._singletons:
            return self._singletons[key]

        if key not in self._factories:
            raise RuntimeError(f"No factory or instance registered for: {key}")

        instance = self._factories[key](self, **kwargs)
        self._singletons[key] = instance

        return instance

    def has(self, key: str) -> bool:
        """Check if a dependency is registered.

        Args:
            key: Dependency key

        Returns:
            True if registered, False otherwise
        """
        return key in self._factories or key in self._instances or key in self._singletons

    def reset(self) -> None:
        """Reset all singleton instances but keep factories."""
        self._singletons.clear()

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._singletons.clear()
        self._factories.clear()
        self._instances.clear()

    def _instantiate(self, cls: type[Any]) -> Any:
        """Instantiate a class with constructor injection.

        Args:
            cls: Class to instantiate

        Returns:
            Instantiated object with dependencies injected
        """
        sig = inspect.signature(cls.__init__)
        dependencies: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            if param.annotation is inspect.Parameter.empty:
                continue

            try:
                dependencies[param_name] = self.resolve(param.annotation.__name__)
            except RuntimeError:
                if param.default is not inspect.Parameter.empty:
                    dependencies[param_name] = param.default
                else:
                    raise

        return cls(**dependencies)


_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get the global DI container instance.

    Returns:
        Global DIContainer instance
    """
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def reset_container() -> None:
    """Reset the global DI container."""
    global _container
    _container = None
