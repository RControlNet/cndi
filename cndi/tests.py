import inspect
from functools import wraps
from typing import Callable

import pytest

from cndi.annotations import constructKeyWordArguments, Component, SingletonContext, getBeanObject
from cndi.initializers import AppInitializer

@Component
class TestContext():
    def __init__(self):
        self.packages = []

def cndi_inject(test_func):
    """Inject CNDI beans for parameters whose type annotation matches a
    registered bean. Leaves all other parameters (pytest fixtures, plain
    args) untouched so pytest's own injection still works normally."""

    @wraps(test_func)
    def wrapper(*args, **kwargs):
        context = SingletonContext()
        sig = inspect.signature(test_func)
        annotations = {
            name: param.annotation
            for name, param in sig.parameters.items()
            if param.annotation is not inspect.Parameter.empty
               and name not in kwargs  # don't override what pytest already injected
        }

        injected = {}
        for param_name, type_hint in annotations.items():
            if not isinstance(type_hint, type):
                continue
            bean_key = f"{type_hint.__module__}.{type_hint.__name__}"
            if bean_key in context.beanStore:
                injected[param_name] = getBeanObject(type_hint)
            # if not in beanStore, leave it alone — pytest or the caller handles it

        return test_func(*args, **{**injected, **kwargs})

    return wrapper

def cndi_pytest_fixture(packages: list[str] = None,
                        freeze: bool = False,
                        preload_callbacks: Callable = lambda: None
                        ):
    """Session-scoped fixture factory that initializes the CNDI context ONCE
    before all tests, without clearing and reinitializing between each test.

    Usage:
        # conftest.py
        from cndi_pytest import cndi_pytest_fixture

        @pytest.fixture(scope="session", autouse=True)
        def cndi_context():
            yield from cndi_pytest_fixture(packages=["your_app_package"])()
    """
    @pytest.fixture(scope="module", autouse=True)
    def _fixture():
        context = SingletonContext()
        # clear once at start of session, not between every test
        context.beans.clear()
        context.validatedBeans.clear()
        context.beanStore.clear()
        context.components.clear()
        context.componentStore.clear()
        context.autowires.clear()
        context._test_scope = True

        # replay any decorators that fired before context was ready
        for replay, obj, kwargs in context.replays:
            replay(obj, **kwargs)

        app = AppInitializer()
        for package in (packages or []):
            app.componentScan(package)
        preload_callbacks()
        app.run(freeze=freeze)

        yield  # all tests run here, context stays alive

        # teardown after ALL tests complete
        context.beans.clear()
        context.validatedBeans.clear()
        context.beanStore.clear()
        context.components.clear()
        context.componentStore.clear()
        context.autowires.clear()
        context._test_scope = False

    return _fixture
