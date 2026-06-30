from functools import wraps
from typing import Callable

from cndi.annotations import constructKeyWordArguments, Component, SingletonContext
from cndi.initializers import AppInitializer

@Component
class TestContext():
    def __init__(self):
        self.packages = []

def cndi_context_test(test_func: Callable):
    """Decorator to initialize Context before running a test."""

    @wraps(test_func)
    def wrapper(self, *args, **kwargs):
        context = SingletonContext()
        context.beans.clear()
        context.validatedBeans.clear()
        context.beanStore.clear()
        context.components.clear()
        context.componentStore.clear()
        context.autowires.clear()
        context._test_scope = True
        for replay, obj, kwargs in context.replays:
            replay(obj, **kwargs)

        # Reset frozen state if applicable
        if hasattr(context, 'frozen'):
            context.frozen = False

        # Initialize the singleton Context instance
        app = AppInitializer()
        app.componentScan('cndi')
        app.run(freeze=False)

        constructed_kwargs = constructKeyWordArguments(test_func.__annotations__)
        # Run the test
        yield test_func(self, *args, **constructed_kwargs,**kwargs)

        context.beans.clear()
        context.validatedBeans.clear()
        context.beanStore.clear()
        context.components.clear()
        context.componentStore.clear()
        context.autowires.clear()
        context._test_scope = False

    return wrapper