"""
This module provides functionality for managing components and beans in the application.

It includes functionality for importing modules, normalizing module and class names, and managing various stores for beans, components, profiles, conditional rendering, and overrides.

Variables:
    validatedBeans: A list of validated beans.
    beans: A list of beans.
    autowires: A list of autowires.
    components: A list of components.
    beanStore: A dictionary storing beans.
    componentStore: A dictionary storing components.
    profilesStores: A dictionary storing profiles.
    conditionalRender: A dictionary storing conditional rendering settings.
    overrideStore: A dictionary storing overrides.

Functions:
    importModuleName: Imports a module given its full name.
    normaliseModuleAndClassName: Normalizes a module and class name.
"""

import logging
import os
import types
from inspect import getfullargspec
from typing import Callable, Any

from cndi.annotations.component import ComponentClass
from cndi.env import RCN_ACTIVE_PROFILE
from cndi.exception import BeanNotFoundException

logger = logging.getLogger("cndi.annotations")

class SingletonContext:
    """Singleton context manager for storing beans, components, and related data."""
    _instance = None
    _frozen = False
    _test_scope = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonContext, cls).__new__(cls)
            cls._instance.validatedBeans = []
            cls._instance.beans = []
            cls._instance.autowires = []
            cls._instance.components = []
            cls._instance.beanStore = {}
            cls._instance.replays = []
            cls._instance.componentStore = {}
            cls._instance.profilesStores = {}
            cls._instance.conditionalRender = {}
            cls._instance.overrideStore = {}
            cls._instance._test_scope = False
        return cls._instance

    def freeze(self):
        """Freeze the context to make all stored values immutable."""
        self.validatedBeans = tuple(self.validatedBeans)
        self.beans = tuple(self.beans)
        self.autowires = tuple(self.autowires)
        self.components = tuple(self.components)
        self.beanStore = types.MappingProxyType(self.beanStore)
        self.componentStore = types.MappingProxyType(self.componentStore)
        self.profilesStores = types.MappingProxyType(self.profilesStores)
        self.conditionalRender = types.MappingProxyType(self.conditionalRender)
        self.overrideStore = types.MappingProxyType(self.overrideStore)
        SingletonContext._frozen = True

    def __setattr__(self, name: str, value: Any) -> None:
        if SingletonContext._frozen:
            raise AttributeError(f"Cannot modify frozen context attribute: {name}")
        super().__setattr__(name, value)

context = SingletonContext()

from functools import wraps
import importlib
import copy


def importModuleName(fullname):
    modules = fullname.split('.')
    module = importlib.import_module(modules[-1], package='.'.join(modules[:-1]))
    return module


def normaliseModuleAndClassName(name):
    nameList: list = name.split(".")
    if "__init__" in nameList:
        nameList.remove("__init__")
    return '.'.join(nameList)


def getBeanObject(objectType):
    """
    Retrieves a bean object from the bean storage.

    This function queries the bean storage for a bean of the specified type. If the bean is found, it returns a new instance of the bean if the 'newInstance' attribute of the bean is True, otherwise it returns the existing instance.

    Args:
        objectType: The type of the bean to retrieve.

    Returns:
        An instance of the bean of the specified type.
    """
    if isinstance(objectType, type) or isinstance(objectType, types.FunctionType):
        objectType = normaliseModuleAndClassName('.'.join([objectType.__module__, objectType.__name__]))
    bean = queryBeanStorage(objectType)
    objectInstance = bean['objectInstance']
    return copy.deepcopy(objectInstance) if bean['newInstance'] else objectInstance


def queryBeanStorage(fullname):
    objectType = normaliseModuleAndClassName(fullname)
    bean = context.beanStore[objectType]
    return bean


class AutowiredClass:
    def __init__(self, required, func, kwargs: dict):
        self.fullname = '.'.join([func.__qualname__])
        self.className = normaliseModuleAndClassName('.'.join(func.__qualname__.split(".")[:-1]))
        self.func = func
        self.kwargs = kwargs
        self.required = required
        self.context = SingletonContext()

    def dependencyInject(self):
        dependencies = self.calculateDependencies()
        dependencyNotFound = list()
        for dependency in dependencies:
            if dependency not in self.context.beanStore:
                dependencyNotFound.append(dependency)

        if len(dependencyNotFound) > 0:
            logger.warning(f"Skipping {self.fullname}")
            assert not self.required, "Could not initialize " + self.fullname + " with beans " + str(
                dependencyNotFound)

        kwargs = self.kwargs
        args = dict()
        for (key, value) in kwargs.items():
            fullName = normaliseModuleAndClassName('.'.join([value.__module__, value.__name__]))
            if fullName in self.context.beanStore:
                args[key] = getBeanObject(fullName)

        if self.className in self.context.beanStore:
            self.func(self.context.beanStore[self.className], **args)
        else:
            logger.debug(f"{self.className} {self.fullname}")
            self.func(**args)

    def calculateDependencies(self):
        return list(
            map(lambda dependency: normaliseModuleAndClassName('.'.join([dependency.__module__, dependency.__name__])),
                self.kwargs.values()))

def _override_bean_type_inner_function(func, type):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    fullname = '.'.join([wrapper.__module__, wrapper.__name__])

    context.overrideStore[fullname] = {
        "func": wrapper,
        "overrideType": type
    }
    return wrapper
def OverrideBeanType(type: object):
    """
    OverrideBeanType is used to override the current annotated @Component class to be injected as some other object

    :param type: Class type to override while performing Dependency Injection
    :return: function wrapper
    """

    def callable(ext_func):
        inner_function = lambda func: _bean_inner_function(func, type)
        replay_context(_bean_inner_function, ext_func, type=type)
        return inner_function(ext_func)

    return callable


def queryOverideBeanStore(fullname):
    if fullname in context.overrideStore:
        return context.overrideStore[fullname]
    else:
        return None

def replay_context(annotation, obj, **kwargs):
    if context._test_scope:
        context.replays.append((annotation, obj, kwargs))
        logger.info(f"Adding Replay for {annotation} {obj}")

def _resolve_function_fullname(wrapper):
    """
    Resolves the full name of a function, including its module and qualified name.

    Args:
        func: The function for which to resolve the full name.
    """
    moduleName = wrapper.__module__[:-9] if wrapper.__module__.endswith(".__init__") else wrapper.__module__
    componentFullName = '.'.join([moduleName, wrapper.__qualname__])
    return componentFullName

def Component(ext_func: object):
    def inner_method(func):
        """
        A decorator that registers a class as a component.
    
        When a class is decorated with @Component, the AppInitializer tries to automatically initialize the class. The class is registered with its full name, which is constructed from the module name and the class name.
    
        Args:
            func: The class to be registered as a component.
    
        Returns:
            The decorated class.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        componentFullName = _resolve_function_fullname(wrapper)
        logger.debug(f"Registering Function name " + componentFullName)
        duplicateComponents = list(filter(lambda component: component.fullname == componentFullName, context.components))
        if duplicateComponents.__len__() > 0:
            logger.debug(f"Duplicate Component found for: {duplicateComponents}")
        else:
            context.components.append(ComponentClass(**{
                'fullname': componentFullName,
                'func': wrapper,
                'annotations': wrapper.__init__.__annotations__ if "__annotations__" in dir(wrapper.__init__) else {}
            }))
        return wrapper
    replay_context(inner_method, ext_func)
    return inner_method(ext_func)

def validateBean(fullname):
    """
    Validates Beans before performing the dependency injection
    :param fullname: bean class full classpath name
    :return: Boolean type
    """

    profile = queryProfileData(fullname)
    condition = queryContitionalRenderingStore(fullname)
    if profile is None and condition is None:
        return True
    flag = True

    if profile is not None:
        profileNames = set(profile['profiles'])
        environmentProfiles = set(map(lambda x: x.strip(), os.environ[RCN_ACTIVE_PROFILE].split(",")))
        intersectionProfiles = profileNames.intersection(environmentProfiles)

        flag &= intersectionProfiles.__len__() >= 1

    if condition is not None:
        callback = condition['callback']
        callbackValue = callback(condition['func'])
        flag &= bool(callbackValue)

    if flag is False:
        logger.debug("Validation Failed for Bean " + fullname)

    return flag

def _bean_inner_function(func, newInstance):
    annotations = func.__annotations__
    logger.debug(f"Registering Bean {func} with annotations {annotations}")
    if  'return' not in annotations:
        if context._test_scope:
            return
        raise Exception(f'Not a valid bean {func}')

    returnType = annotations['return']
    del annotations['return']

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    fullname = _resolve_function_fullname(returnType)
    annotations = dict(
        map(lambda key: (key, '.'.join([annotations[key].__module__, annotations[key].__qualname__])), annotations))

    duplicate_beans = [b for b in context.beans if b['name'] == fullname]
    if duplicate_beans:
        logger.debug(f"Duplicate Bean found for: {fullname} — skipping registration")
        return wrapper

    if validateBean(fullname):
        context.beans.append({
            'name': fullname,
            'newInstance': newInstance,
            'object': wrapper,
            'fullname': wrapper.__qualname__,
            'kwargs': annotations,
            'index': len(context.beans)
        })

        return wrapper
    else:
        return None

def Bean(newInstance=False):
    """

    :param newInstance:
    :return:
    """
    def callable(ext_func):
        inner_function = lambda func: _bean_inner_function(func, newInstance)
        replay_context(_bean_inner_function, ext_func, newInstance=newInstance)
        return inner_function(ext_func)

    return callable

def _conditional_rendering_inner_function(func, callback=lambda method: True, overrideFullName = None):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    fullname = ".".join([wrapper.__module__, wrapper.__qualname__]) if overrideFullName is None else overrideFullName

    context.conditionalRender[fullname] = {
        "func": wrapper,
        "callback": callback
    }

    return wrapper

def ConditionalRendering(callback=lambda method: True, overrideFullName = None):
    """
    A decorator that conditionally renders a class based on a callback function.

    This decorator checks the return value of the provided callback function. If the callback returns True, the class is rendered. If the callback returns False, the class is not rendered.

    Args:
        callback: A function that determines whether the class should be rendered. This function should take no arguments and return a boolean.

    Returns:
        The decorated class, if the callback returns True. None, if the callback returns False.
    """

    def callable(ext_func):
        inner_function = lambda func: _conditional_rendering_inner_function(func, callback=callback, overrideFullName = overrideFullName)
        replay_context(_conditional_rendering_inner_function, ext_func, callback=callback, overrideFullName = overrideFullName)
        return inner_function(ext_func)


    return callable


def queryContitionalRenderingStore(fullname):
    if fullname in context.conditionalRender:
        return context.conditionalRender[fullname]
    else:
        return None

def constructKeyWordArguments(annotations, required=True):
    kwargs = dict()
    for key, classObject in annotations.items():
        beanName = f"{classObject.__module__}.{classObject.__name__}"
        if beanName in context.beanStore:
            kwargs[key] = getBeanObject(beanName)
        elif required:
            raise BeanNotFoundException(f"Following Bean failed to load in SingletonContext: "+beanName)
        else:
            logger.warn(f"Bean not found {beanName} and required is set to false")
    return kwargs

def _profile_inner_function(func, profiles):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    fullname = ".".join([wrapper.__module__, wrapper.__qualname__])
    context.profilesStores[fullname] = {
        "func": wrapper,
        "profiles": profiles
    }

    return wrapper

def Profile(profiles=["default"]):
    """

    :param profiles:
    :return:
    """

    def callable(ext_func):
        inner_function = lambda func: _profile_inner_function(func,profiles=profiles)
        replay_context(_profile_inner_function, ext_func, profiles=profiles)
        return inner_function(ext_func)


    return callable


def queryProfileData(fullname):
    if fullname in context.profilesStores:
        return context.profilesStores.get(fullname)
    else:
        return None


def _autowired_inner_function(func, required):
    annotations = func.__annotations__

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    context.autowires.append(AutowiredClass(required=required, **{
        'kwargs': annotations,
        'func': wrapper
    }))

    return wrapper


def Autowired(required=True):
    """
    
    :param required:
    :return:
    """

    def callable(ext_func):
        inner_function = lambda func: _autowired_inner_function(func,required=required)
        replay_context(_autowired_inner_function, ext_func, required=required)
        return inner_function(ext_func)

    return callable

def getBean(beans, name):
    return list(filter(lambda x: x['name'] == name, beans))[0]


def workOrder(beans):
    allBeanNames = list(map(lambda bean: bean['name'], beans))
    beanQueue = list(filter(lambda bean: len(bean['kwargs']) == 0, beans))
    beanIndexes = list(map(lambda bean: bean['index'], beanQueue))

    beanDependents = list(filter(lambda bean: bean['index'] not in beanIndexes, beans))
    beanQueueNames = list(map(lambda bean: bean['name'], beanQueue))

    for i in range(len(beanQueue)):
        beanQueue[i]['index'] = i

    for dependents in beanDependents:
        args = list(dependents['kwargs'].values())
        flag = True
        for argClassName in args:
            if (argClassName not in beanQueueNames and argClassName in allBeanNames) or argClassName in beanQueueNames:
                flag = flag and True
                dependents['index'] = getBean(beans, argClassName)['index'] + max(beanIndexes)
            else:
                flag = False

        if flag:
            beanQueue.append(dependents)
            beanQueueNames.append(dependents['name'])

    assert len(beanQueue) == len(beans), "Somebeans were not initialized properly"
    return list(sorted(beanQueue, key=lambda x: x['index']))
