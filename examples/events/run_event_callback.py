from cndi.annotations import Autowired, Component, Bean
from cndi.annotations.events import OnEvent, EventBus, BuiltInEventsTypes
from cndi.consts import RCN_ENABLE_STANDALONE_MESSAGE_BROKER, RCN_ENABLE_CONTEXT_THREADS, RCN_EVENTS_ENABLE
from cndi.env import RCN_ENVS_CONFIG
from cndi.initializers import AppInitializer
import os

os.environ[RCN_ENVS_CONFIG + '.' + RCN_ENABLE_STANDALONE_MESSAGE_BROKER] = "True"
os.environ[RCN_ENVS_CONFIG + '.' + RCN_ENABLE_CONTEXT_THREADS] = "True"
os.environ[RCN_ENVS_CONFIG + '.' + RCN_EVENTS_ENABLE] = "True"

@OnEvent("on_load")
async def on_load_1():
    print("Called Func 1")

@OnEvent(BuiltInEventsTypes.ON_CONTEXT_LOAD)
def on_load_2(object: EventBus):
    print("Called Func 2", object)
    object.publish("on_load")                 # Execute using Event Bus

@OnEvent("on_load_3")
def on_load_3(test: str, object: EventBus):
    print("Called Func 3", test)

@OnEvent(BuiltInEventsTypes.ON_CONTEXT_LOAD)
def on_context_load():
    print("SingletonContext Loaded")

@Autowired()
def setEventExecutor(eventBus: EventBus):
    eventBus.publish("on_load_3", data=dict(test="Hello"))                 # Execute using Event Bus

if __name__ == '__main__':
    app_initializer = AppInitializer()
    app_initializer.run()