import os
from cndi.annotations import ConditionalRendering, Component, Bean, Autowired
from cndi.initializers import AppInitializer

os.environ['TEST'] = "True"


@Component
@ConditionalRendering(callback=lambda x: "TEST" in os.environ)
class TestConditionalAnnotation:
    def __init__(self):
        print("Initialized")

    def postConstruct(self):
        print("Called Post Construct")

if __name__ == '__main__':
    app = AppInitializer()
    app.componentScan('cndi')
    app.run()