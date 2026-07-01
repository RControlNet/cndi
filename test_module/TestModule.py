import os

from cndi.env import RCN_ACTIVE_PROFILE


from cndi.annotations import Bean, Profile
from test_module.TestBean import TestBean

@Profile(profiles=['hello'])
@Bean()
def getTestBean() -> TestBean:
    return TestBean("Test 123")

@Bean()
@Profile(profiles=['default'])
def getTestBean1() -> TestBean:
    return TestBean("Test 453")