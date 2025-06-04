import unittest
import io
import os
import sys
import yaml

# Add the path to the plugins directory
current_dir = os.path.dirname(os.path.abspath(__file__))
plugins_dir = os.path.join(current_dir, "../../../../plugins")
sys.path.insert(0, plugins_dir)

# Import the module directly
from module_utils.yaml_utils import (
    safe_dump,
    safe_load,
    CustomYAMLDumper,
    InheritableDict,
    represent_undefined
)


class TestYamlUtils(unittest.TestCase):
    """Test cases for the YAML utilities module."""

    def test_safe_dump_normal(self):
        """Test that safe_dump properly dumps regular YAML data."""
        data = {'key': 'value', 'list': [1, 2, 3], 'nested': {'a': 'b'}}
        output = io.StringIO()
        safe_dump(data, output)
        result = output.getvalue()

        self.assertIn('key: value', result)
        self.assertIn('list:', result)
        self.assertIn('- 1', result)
        self.assertIn('nested:', result)
        self.assertIn('  a: b', result)

    def test_safe_dump_inherit_tag(self):
        """Test that safe_dump preserves !inherit tags."""
        data = {'key': '!inherit', 'regular': 'value'}
        output = io.StringIO()
        safe_dump(data, output)
        result = output.getvalue()

        # The actual output has quotes around the !inherit tag
        self.assertIn("key: '!inherit'", result)
        self.assertIn('regular: value', result)

    def test_represent_undefined_inherit(self):
        """Test the represent_undefined function with !inherit value."""
        dumper = CustomYAMLDumper(io.StringIO())
        node = represent_undefined(dumper, '!inherit')

        self.assertEqual(node.tag, '!inherit')
        self.assertEqual(node.value, '')

    def test_represent_undefined_regular_string(self):
        """Test the represent_undefined function with a regular string."""
        dumper = CustomYAMLDumper(io.StringIO())
        node = represent_undefined(dumper, 'regular_string')

        self.assertEqual(node.tag, 'tag:yaml.org,2002:str')
        self.assertEqual(node.value, 'regular_string')

    def test_safe_dump_with_options(self):
        """Test safe_dump with custom options."""
        data = {'key': 'value'}
        output = io.StringIO()
        safe_dump(data, output, default_flow_style=True)
        result = output.getvalue()

        self.assertEqual(result.strip(), '{key: value}')

    def test_safe_dump_none_value(self):
        """Test safe_dump with None value."""
        data = {'key': None}
        output = io.StringIO()
        safe_dump(data, output)
        result = output.getvalue()

        self.assertIn('key:', result)
        self.assertNotIn('key: null', result)

    def test_round_trip_with_inherit_tag(self):
        """Test round-trip parsing and serialization of YAML with !inherit tag."""
        # Original YAML string with !inherit tag
        original_yaml = """foo: !inherit
  bar: 1
  baz: true
"""
        # Parse the YAML string with our custom loader
        parsed_data = safe_load(original_yaml)

        # For comparison with standard YAML (without !inherit tag)
        standard_yaml = """foo:
  bar: 1
  baz: true
"""
        standard_data = yaml.safe_load(standard_yaml)

        # Verify the data structure after parsing
        self.assertIsInstance(parsed_data['foo'], InheritableDict)
        self.assertEqual(parsed_data['foo'].tag, '!inherit')
        self.assertEqual(parsed_data['foo']['bar'], 1)
        self.assertEqual(parsed_data['foo']['baz'], True)

        # Our parsed data should have the tag, standard shouldn't
        self.assertNotEqual(type(parsed_data['foo']), type(standard_data['foo']))

        # Serialize back to YAML
        output = io.StringIO()
        safe_dump(parsed_data, output)
        result = output.getvalue()

        # Our serialization should match the original
        self.assertEqual(original_yaml, result)

        # Standard output should be different (it wouldn't have the tag)
        standard_output = io.StringIO()
        yaml.safe_dump(standard_data, standard_output)
        self.assertNotEqual(original_yaml, standard_output.getvalue())

        # Parse the serialized YAML again to verify structure
        reparsed_data = safe_load(result)

        # Verify the round-trip preserves the tag and data
        self.assertIsInstance(reparsed_data['foo'], InheritableDict)
        self.assertEqual(reparsed_data['foo'].tag, '!inherit')
        self.assertEqual(reparsed_data['foo']['bar'], 1)
        self.assertEqual(reparsed_data['foo']['baz'], True)


if __name__ == '__main__':
    unittest.main()