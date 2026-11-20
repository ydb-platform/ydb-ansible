import yaml
import io
from collections.abc import Mapping
from ansible.errors import AnsibleFilterError
from ansible.module_utils.six import string_types
from ansible.utils.display import Display

DOCUMENTATION = r'''
    name: yaml_filters
    plugin_type: filter
    short_description: YAML config parsing
    description: |
        YAML config parsing
'''

display = Display()

class YDBDynCustomYAMLDumper(yaml.SafeDumper):
    """
    Custom YAML Dumper with improved formatting
    """
    def increase_indent(self, flow=False, indentless=False):
        return super(YDBDynCustomYAMLDumper, self).increase_indent(flow, False)

# Add representers for Python types if needed
def dict_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

YDBDynCustomYAMLDumper.add_representer(dict, dict_representer)

def _to_plain(data):
    """
    Copy data into plain Python types, which yaml.SafeDumper can represent.

    Since ansible-core 2.19, templated values arrive as subclasses of dict, list,
    str and the number types. SafeDumper looks representers up by exact type, so
    it cannot represent them, and the dump would fall back to str().
    """
    if isinstance(data, Mapping):
        return {_to_plain(key): _to_plain(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [_to_plain(item) for item in data]
    if isinstance(data, bool):
        return bool(data)
    if isinstance(data, int):
        return int(data)
    if isinstance(data, float):
        return float(data)
    if isinstance(data, str):
        return str(data)
    return data

def ydb_config_to_yaml(a, indent=2, *args, **kw):
    """
    A custom variant of to_nice_yaml that ensures proper formatting
    and preserves structure of the input data.

    Args:
        a: The data to convert to YAML
        indent: The indentation level (default: 2)
        *args, **kw: Additional arguments passed to yaml.dump

    Returns:
        A formatted YAML string
    """
    a = _to_plain(a)
    try:
        output = io.StringIO()
        yaml.dump(
            a,
            output,
            Dumper=YDBDynCustomYAMLDumper,
            indent=indent,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,  # Preserve key order
            width=80,  # Line width
            **kw
        )
        return output.getvalue()
    except Exception as e:
        # Fallback to basic string representation if YAML dumping fails
        try:
            # Try with safe dumper
            output = io.StringIO()
            yaml.dump(
                a,
                output,
                Dumper=yaml.SafeDumper,
                indent=indent,
                allow_unicode=True,
                default_flow_style=False,
                **kw
            )
            return output.getvalue()
        except Exception as e2:
            # Last resort - return string representation
            display.warning(f"YAML dumping failed twice: {e}, {e2}")
            return str(a)


class FilterModule(object):
    """
    Custom YAML filter plugins for Ansible
    """

    def filters(self):
        display.vvv("Registering ydb_platform.ydb.ydb_config_to_yaml filter")
        # Register the filter both with and without collection prefix for maximum compatibility
        return {
            'ydb_config_to_yaml': ydb_config_to_yaml,
            'ydb_platform.ydb.ydb_config_to_yaml': ydb_config_to_yaml,
        }