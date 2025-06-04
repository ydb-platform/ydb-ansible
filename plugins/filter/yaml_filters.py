import yaml
import io
from ansible.errors import AnsibleFilterError
from ansible.module_utils.six import string_types
from ansible.utils.display import Display

display = Display()

class CustomYAMLDumper(yaml.SafeDumper):
    """
    Custom YAML Dumper with improved formatting
    """
    def increase_indent(self, flow=False, indentless=False):
        return super(CustomYAMLDumper, self).increase_indent(flow, False)

# Add representers for Python types if needed
def dict_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

CustomYAMLDumper.add_representer(dict, dict_representer)

def custom_to_nice_yaml(a, indent=2, *args, **kw):
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
    try:
        output = io.StringIO()
        yaml.dump(
            a,
            output,
            Dumper=CustomYAMLDumper,
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
        display.vvv("Registering ydb_platform.ydb.custom_to_nice_yaml filter")
        # Register the filter both with and without collection prefix for maximum compatibility
        return {
            'custom_to_nice_yaml': custom_to_nice_yaml,
            'ydb_platform.ydb.custom_to_nice_yaml': custom_to_nice_yaml,
        }