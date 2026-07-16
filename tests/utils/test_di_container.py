"""Tests for dependency injection container."""

from lenovo_tool.core.di_container import DIContainer


class DatabaseInterface:
    """Mock interface for testing."""

    def get_name(self) -> str:
        """Get database name."""


class MySQLDatabase(DatabaseInterface):
    """Mock MySQL implementation."""

    def get_name(self) -> str:
        """Get database name."""
        return "MySQL"


class PostgreSQLDatabase(DatabaseInterface):
    """Mock PostgreSQL implementation."""

    def get_name(self) -> str:
        """Get database name."""
        return "PostgreSQL"


class ServiceWithDependency:
    """Service that depends on DatabaseInterface."""

    def __init__(self, db: DatabaseInterface) -> None:
        self.db = db

    def get_db_name(self) -> str:
        """Get database name through dependency."""
        return self.db.get_name()


class ServiceWithDefaultParam:
    """Service with optional dependency."""

    def __init__(self, db: DatabaseInterface | None = None) -> None:
        self.db = db

    def get_db_name(self) -> str:
        """Get database name."""
        return self.db.get_name() if self.db else "No DB"


def test_register_and_resolve_factory():
    """Container should register and resolve a factory function."""
    container = DIContainer()

    def db_factory(_):
        return MySQLDatabase()

    container.register_factory("DatabaseInterface", db_factory)

    instance = container.resolve("DatabaseInterface")

    assert isinstance(instance, MySQLDatabase)
    assert instance.get_name() == "MySQL"


def test_register_and_resolve_instance():
    """Container should register and resolve a singleton instance."""
    container = DIContainer()
    container.register_instance("DatabaseInterface", PostgreSQLDatabase())

    instance = container.resolve("DatabaseInterface")

    assert isinstance(instance, PostgreSQLDatabase)
    assert instance.get_name() == "PostgreSQL"


def test_singleton_management():
    """Container should return the same instance for singletons."""
    container = DIContainer()

    def db_factory(_):
        return MySQLDatabase()

    container.register_factory("DatabaseInterface", db_factory)

    instance1 = container.resolve("DatabaseInterface")
    instance2 = container.resolve("DatabaseInterface")

    assert instance1 is instance2


def test_resolve_with_kwargs():
    """Container should pass kwargs to factory."""
    container = DIContainer()

    def service_factory(_, db_name: str):
        class NamedDB(DatabaseInterface):
            def get_name(self):
                return db_name
        return NamedDB()

    container.register_factory("NamedDB", service_factory)

    instance = container.resolve("NamedDB", db_name="CustomDB")
    assert instance.get_name() == "CustomDB"


def test_container_has_method():
    """Container should have correct has() behavior."""
    container = DIContainer()

    def db_factory(_):
        return MySQLDatabase()

    container.register_factory("DatabaseInterface", db_factory)

    assert container.has("DatabaseInterface")
    assert not container.has("NonExistent")


def test_resolve_unregistered_dependency():
    """Container should raise error for unregistered dependency."""
    container = DIContainer()

    try:
        container.resolve("DatabaseInterface")
        assert False, "Should raise RuntimeError"
    except RuntimeError as e:
        assert "registered" in str(e)


def test_clear_removes_all_registrations():
    """Container should clear all instances but keep factories."""
    container = DIContainer()

    def db_factory(_):
        return MySQLDatabase()

    container.register_factory("DatabaseInterface", db_factory)
    instance1 = container.resolve("DatabaseInterface")

    container.reset()

    instance2 = container.resolve("DatabaseInterface")

    assert instance1 is not instance2
    assert isinstance(instance2, MySQLDatabase)


def test_nested_dependencies():
    """Container should resolve nested dependencies."""

    class Repository:
        def __init__(self, db: DatabaseInterface) -> None:
            self.db = db

    class Service:
        def __init__(self, repo: Repository) -> None:
            self.repo = repo

    container = DIContainer()

    def db_factory(_):
        return MySQLDatabase()

    def repo_factory(_):
        return Repository(container.resolve("DatabaseInterface"))

    def service_factory(_):
        return Service(container.resolve("Repository"))

    container.register_factory("DatabaseInterface", db_factory)
    container.register_factory("Repository", repo_factory)
    container.register_factory("Service", service_factory)

    service = container.resolve("Service")

    assert isinstance(service, Service)
    assert isinstance(service.repo, Repository)
    assert isinstance(service.repo.db, MySQLDatabase)