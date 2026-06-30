import os
import unittest
from pathlib import Path

from cndi.resources import ResourceFinder
from cndi.tests import cndi_context_test

class ResourceFinderTest(unittest.TestCase):
    @cndi_context_test
    def test_find_resource(self, resource_finder: ResourceFinder):
        self.assertIsNotNone(resource_finder)

    @cndi_context_test
    def test_find_resource_success(self, resource_finder: ResourceFinder):
        # Create a temporary resource file for testing
        resource_path = resource_finder.computeResourcePath()
        os.makedirs(resource_path, exist_ok=True)
        test_resource_path = f"{resource_path}/test_resource.txt"
        with open(test_resource_path, 'w') as f:
            f.write("This is a test resource.")

        # Test finding the resource
        found_resource_path = resource_finder.findResource("test_resource.txt")
        self.assertEqual(found_resource_path, Path(test_resource_path))

        os.remove(test_resource_path)
        self.assertFalse(os.path.exists(test_resource_path))

    @cndi_context_test
    def test_find_resource_not_found(self, resource_finder: ResourceFinder):
        with self.assertRaises(FileNotFoundError):
            resource_finder.findResource("non_existent_resource.txt")
