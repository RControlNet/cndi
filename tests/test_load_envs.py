import unittest

from cndi.tests import cndi_context_test

RCN_ENVS_CONFIG = 'RCN_ENVS_CONFIG'

from cndi.env import loadEnvFromFile, getContextEnvironment, VARS


class LoadEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        VARS.clear()
        VARS[f"{RCN_ENVS_CONFIG}.active.profile".lower()] = "test"

    @cndi_context_test
    def testloadEnvFromFile(self):
        self.assertEqual("test", getContextEnvironment("rcn.profile"))
    @cndi_context_test
    def testloadEnvWithListDatatype(self):

        self.assertEqual(getContextEnvironment('mini.listdata.#1.name'), 'thereitis')
        self.assertEqual(getContextEnvironment('mini.listdata.#0.page.#0.default'), '2')
