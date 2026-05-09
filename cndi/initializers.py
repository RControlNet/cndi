import copy
import importlib
import logging
import os
import time

from cndi.annotations import workOrder, getBeanObject, \
    validateBean, queryOverideBeanStore, constructKeyWordArguments, SingletonContext
from cndi.annotations.events import EventBus, BuiltInEventsTypes
from cndi.binders.message import DefaultMessageBinder
from cndi.consts import RCN_EVENTS_ENABLE
from cndi.env import loadEnvFromFile, getContextEnvironment, reload_envs, getConfiguredProfile
from cndi.flask.flask_app import FlaskApplication
from cndi.http.management import ManagementServer
from cndi.utils import importSubModules
from cndi.version import VERSION

logger = logging.getLogger(__name__)

initializerComponents = [
    '.'.join([ManagementServer.__module__, ManagementServer.__name__]),
    '.'.join([FlaskApplication.__module__, FlaskApplication.__name__])
]

def on_context_load(event_bus: EventBus):
    event_bus.publish(BuiltInEventsTypes.ON_CONTEXT_LOAD)
    logger.info("App Started Successfully")

class AppInitializer:
    def __init__(self):
        """
        Responsible to initialise Dependency Injection for Application
        """
        self.context = SingletonContext()
        profile = getConfiguredProfile()
        logger.info(f"CNDI Version: v{VERSION}")
        logger.info(f"Configured Profile: {profile}")
        try:
            from dotenv import load_dotenv
            load_dotenv("./.env")
            reload_envs()
        except ImportError as e:
            logger.error(e)
        self.componentsPath = list()
        applicationYml = "resources/application.yml"

        if os.path.exists(applicationYml):
            logger.info(f"External Configuration found: {applicationYml}")
            loadEnvFromFile(applicationYml)

    def componentScan(self, module):
        importModule = importlib.import_module(module)
        self.componentsPath.append(importModule)

    def run(self, onComplete = on_context_load, freeze=True):
        """
        Performing Dependency Injection, on priority basis
        Steps Involved in DI
            1. Load Modules and Sub Modules for Bean/Component scanning
            2. Create list for the Available Beans and Components
            3. Resolve Dependency Tree for Beans and Components and Sort in reverse tree dependency
            4. For component classes run postConstruct method if available
            5. Read Configuration for binders and initialise binders for given type (i.e rabbitmq, mqtt)
            6. Perform Dependency Injection by calling setter methods
            7. Start Binder Configuration
        :return: None
        """

        start_time = time.time()

        for module in self.componentsPath:
            importSubModules(module)

        for bean in self.context.beans:
            validBean = validateBean(bean['fullname'])
            if not validBean:
                continue
            else:
                self.context.validatedBeans.append(bean)

        workOrderBeans = workOrder(self.context.validatedBeans)

        for bean in workOrderBeans:
            logger.debug(f"Registering Bean {bean['fullname']}")
            kwargs = dict()
            for key, className in bean['kwargs'].items():
                tempBean = self.context.beanStore[className]
                kwargs[key] = copy.deepcopy(tempBean['object']) if tempBean['newInstance'] else tempBean['object']

            functionObject = bean['object']
            fullname = ".".join([functionObject.__module__, functionObject.__qualname__])
            validBean = validateBean(fullname)
            if validBean:
                bean['objectInstance'] = bean['object'](**kwargs)
                self.context.beanStore[bean['name']] = bean
            else:
                logger.debug(f"Ignoring Bean {fullname} due to bean not satisfy")

        for component in self.context.components:
            validBean = validateBean(component.fullname)
            if not validBean:
                logger.debug(f"Ignoring Component {component.fullname} due to bean not satisfy")
                continue

            self.context.componentStore[component.fullname] = component
            logger.debug(f"Building Component: {component.fullname}")
            kwargs = constructKeyWordArguments(component.annotations)
            objectInstance = component.func(**kwargs)
            if 'postConstruct' in dir(objectInstance):
                postConstructKwargs = constructKeyWordArguments(objectInstance.postConstruct.__annotations__)
                objectInstance.postConstruct(**postConstructKwargs)

            override = queryOverideBeanStore(component.fullname)
            if override is not None:
                overrideType = override['overrideType']
                component.fullname = ".".join([overrideType.__module__, overrideType.__name__])

            self.context.beanStore[component.fullname] = dict(objectInstance=objectInstance,
                                                 name=component.fullname,
                                                 object=objectInstance, index=0, newInstance=False,
                                                 fullname=component.func.__name__, kwargs=kwargs)

        if freeze:
            self.context.freeze()

        messageBinderEnabled = getContextEnvironment("rcn.binders.message.enable", defaultValue=False, castFunc=bool)
        defaultMessageBinder = None

        if messageBinderEnabled:
            defaultMessageBinder = getBeanObject(".".join([DefaultMessageBinder.__module__, DefaultMessageBinder.__name__]))
            defaultMessageBinder.performInjection()

        for autowire in self.context.autowires:
            autowire.dependencyInject()

        if defaultMessageBinder is not None:
            defaultMessageBinder.start()

        for componentName, componentClass in self.context.componentStore.items():
            if componentName in initializerComponents:
                objectInstance = getBeanObject(componentName)
                componentClass.func.run(objectInstance)

        if onComplete is on_context_load and not getContextEnvironment(RCN_EVENTS_ENABLE, defaultValue=False, castFunc=bool):
            logger.warning("SingletonContext Load Event is not published because Events is disable, please enable it by setting RCN_EVENTS_ENABLE to true")
        else:
            kwargs = constructKeyWordArguments(onComplete.__annotations__)
            onComplete(**kwargs)

        end_time = time.time()
        logger.info(f"App Initialisation Completed in {round(end_time - start_time, 2)} seconds")