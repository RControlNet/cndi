import unittest

from cndi.tests import test_with_context

RCN_ENVS_CONFIG = 'RCN_ENVS_CONFIG'

from cndi.env import loadEnvFromFile, getContextEnvironment, VARS


class LoadEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        VARS.clear()
        VARS[f"{RCN_ENVS_CONFIG}.active.profile".lower()] = "test"

    @test_with_context
    def testloadEnvFromFile(self):
        self.assertEqual("test", getContextEnvironment("rcn.profile"))
    @test_with_context
    def testloadEnvWithListDatatype(self):

        self.assertEqual(getContextEnvironment('mini.listdata.#1.name'), 'thereitis')
        self.assertEqual(getContextEnvironment('mini.listdata.#0.page.#0.default'), '2')
