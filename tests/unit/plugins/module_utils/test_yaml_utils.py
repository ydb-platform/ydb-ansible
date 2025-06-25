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
    YDBDynCustomYAMLDumper,
    InheritableDict,
    represent_undefined,
    represent_none
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
        dumper = YDBDynCustomYAMLDumper(io.StringIO())
        node = represent_undefined(dumper, '!inherit')

        self.assertEqual(node.tag, '!inherit')
        self.assertEqual(node.value, '')

    def test_represent_undefined_regular_string(self):
        """Test the represent_undefined function with a regular string."""
        dumper = YDBDynCustomYAMLDumper(io.StringIO())
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

        # With the new represent_none function, None should be properly serialized as null
        self.assertIn('key: null', result)
        # Ensure it's actually null, not the string "None"
        self.assertNotIn('key: None', result)

    def test_represent_none_function(self):
        """Test the represent_none function directly."""
        dumper = YDBDynCustomYAMLDumper(io.StringIO())
        node = represent_none(dumper, None)

        self.assertEqual(node.tag, 'tag:yaml.org,2002:null')
        self.assertEqual(node.value, 'null')

    def test_none_value_round_trip(self):
        """Test round-trip serialization and parsing of None values."""
        original_data = {'key': None, 'other': 'value'}

        # Serialize to YAML
        output = io.StringIO()
        safe_dump(original_data, output)
        yaml_string = output.getvalue()

        # Should contain proper null representation
        self.assertIn('key: null', yaml_string)
        self.assertIn('other: value', yaml_string)

        # Parse back from YAML
        parsed_data = safe_load(yaml_string)

        # Should get back the original structure
        self.assertEqual(parsed_data['key'], None)
        self.assertEqual(parsed_data['other'], 'value')
        self.assertEqual(original_data, parsed_data)

    def test_mixed_none_and_inherit_values(self):
        """Test that None values and !inherit tags can coexist properly."""
        # Create data with both None and !inherit
        inherit_dict = InheritableDict({'nested': 'value'})
        inherit_dict.tag = '!inherit'

        data = {
            'none_value': None,
            'inherit_value': inherit_dict,
            'regular_value': 'test'
        }

        # Serialize
        output = io.StringIO()
        safe_dump(data, output)
        result = output.getvalue()

        # Check that both are handled correctly
        self.assertIn('none_value: null', result)
        self.assertIn('inherit_value: !inherit', result)
        self.assertIn('regular_value: test', result)

        # Parse back and verify
        parsed = safe_load(result)
        self.assertEqual(parsed['none_value'], None)
        self.assertIsInstance(parsed['inherit_value'], InheritableDict)
        self.assertEqual(parsed['inherit_value'].tag, '!inherit')
        self.assertEqual(parsed['regular_value'], 'test')

    def test_nested_none_values(self):
        """Test None values in nested structures."""
        data = {
            'level1': {
                'level2': {
                    'none_key': None,
                    'valid_key': 'value'
                },
                'list_with_none': [1, None, 'string', None]
            }
        }

        # Serialize
        output = io.StringIO()
        safe_dump(data, output)
        result = output.getvalue()

        # Should contain multiple null values
        null_count = result.count('null')
        self.assertEqual(null_count, 3)  # Two in list, one in nested dict

        # Parse back and verify structure
        parsed = safe_load(result)
        self.assertEqual(parsed['level1']['level2']['none_key'], None)
        self.assertEqual(parsed['level1']['level2']['valid_key'], 'value')
        self.assertEqual(parsed['level1']['list_with_none'], [1, None, 'string', None])

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