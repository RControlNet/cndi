import os
from pathlib import Path

import pytest
import logging
from cndi.annotations import getBeanObject
from cndi.annotations import SingletonContext
from cndi.tests import cndi_pytest_fixture, cndi_inject

logger = logging.getLogger(__name__)

cndi_context = cndi_pytest_fixture(packages=["cndi"], freeze=False)

@pytest.fixture(scope="module")
def resource_finder(cndi_context):

    from cndi.resources import ResourceFinder
    logger.info(f"Initializing ResourceFinder bean for tests. {type(ResourceFinder)}")
    logger.info("Available Beans in context: %s", list(SingletonContext().beanStore.keys()))
    return getBeanObject(ResourceFinder)

@cndi_inject
def test_find_resource(resource_finder):
    assert resource_finder is not None


@cndi_inject
def test_find_resource_success(resource_finder):
    # Create a temporary resource file for testing
    resource_path = resource_finder.computeResourcePath()
    os.makedirs(resource_path, exist_ok=True)
    test_resource_path = f"{resource_path}/test_resource.txt"
    with open(test_resource_path, 'w') as f:
        f.write("This is a test resource.")

    # Test finding the resource
    found_resource_path = resource_finder.findResource("test_resource.txt")
    assert found_resource_path==Path(test_resource_path)

    os.remove(test_resource_path)
    assert not (os.path.exists(test_resource_path))