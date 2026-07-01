import pytest
from cndi.annotations import Bean, SingletonContext
from cndi.tests import cndi_pytest_fixture, cndi_inject
import logging

logger = logging.getLogger(__name__)

class BeanTest:
    def __init__(self, name):
        self.name = name

def register_beans():
    @Bean()
    def getTestBean() -> BeanTest:
        logger.info(f"Bean Test: {BeanTest}")
        return BeanTest("Hello")

cndi_context = cndi_pytest_fixture(packages=["cndi", "tests.cndi"], freeze=False, preload_callbacks=register_beans)

@pytest.fixture(scope="module")
def bean_test(cndi_context):
    from cndi.annotations import getBeanObject

    logger.info("Available Beans in context: %s", list(SingletonContext().beanStore.keys()))
    return getBeanObject(BeanTest)

@cndi_inject
def testComponentScanAndDI(bean_test: BeanTest):

    assert bean_test is not None
    assert bean_test.name == "Hello"

