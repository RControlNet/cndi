from cndi.annotations import Bean, Component, SingletonContext
from cndi.initializers import AppInitializer
from test_module.TestBean import TestBean


class TestBean2:
    def __init__(self, name: str):
        self.name = name

@Bean()
def bean_test() -> TestBean:
    return TestBean("Test Component")

@Bean()
def bean_test2(test_bean: TestBean) -> TestBean2:
    assert type(test_bean) is TestBean
    print("Test Bean Injected ", test_bean)
    return TestBean2("Test Component 2")

@Component
class InjectBeanComponent:
    def __init__(self, testBean: TestBean, testBean2: TestBean2):
        self.bean = testBean

        assert type(self.bean) is TestBean
        assert type(testBean2) is TestBean2

def complete(testBean: TestBean):
    print("Start up Completed ", testBean)

if __name__ == "__main__":
    app = AppInitializer()
    app.run(onComplete=complete)