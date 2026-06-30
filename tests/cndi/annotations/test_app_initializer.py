import unittest
from cndi.annotations import Bean
from cndi.tests import cndi_context_test
from test_module.TestBean import TestBean

@Bean()
def getTestBean() -> TestBean:
    return TestBean("Hello")

class AppInitializerTest(unittest.TestCase):
    @cndi_context_test
    def testComponentScanAndDI(self, testBean: TestBean):
        self.assertIsNotNone(testBean)
        self.assertEqual(testBean.name, "Hello")
