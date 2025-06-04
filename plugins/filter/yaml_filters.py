import yaml
import io
from ansible.errors import AnsibleFilterError
from ansible.module_utils.six import string_types
from ansible.utils.display import Display
from ansible.module_utils.common._collections_compat import MutableMapping

display = Display()

# First try a relative import (for development)
try:
    from ..module_utils.yaml_utils import CustomYAMLDumper
    HAS_CUSTOM_DUMPER = True
except ImportError:
    # Then try the collection-qualified import (for installed collection)
    try:
        from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import CustomYAMLDumper
        HAS_CUSTOM_DUMPER = True
    except ImportError:
        display.warning("Unable to import CustomYAMLDumper from yaml_utils module, falling back to standard dumper")
        HAS_CUSTOM_DUMPER = False


def custom_to_nice_yaml(a, indent=4, *args, **kw):
    """
    A custom variant of to_nice_yaml that preserves !inherit tags
    """
    if not HAS_CUSTOM_DUMPER:
        display.warning("ydb_platform.ydb.yaml_utils module not available, falling back to standard YAML dumper")
        try:
            transformed = yaml.dump(
                a,
                Dumper=yaml.SafeDumper,
                indent=indent,
                allow_unicode=True,
                default_flow_style=False,
                **kw
            )
        except Exception as e:
            raise AnsibleFilterError(f"custom_to_nice_yaml filter error: {e}")
        return transformed

    try:
        output = io.StringIO()
        yaml.dump(
            a,
            output,
            Dumper=CustomYAMLDumper,
            indent=indent,
            allow_unicode=True,
            default_flow_style=False,
            **kw
        )
        return output.getvalue()
    except Exception as e:
        raise AnsibleFilterError(f"custom_to_nice_yaml filter error: {e}")


class FilterModule(object):
    """Custom YAML filter plugins for Ansible"""

    def filters(self):
        return {
            'custom_to_nice_yaml': custom_to_nice_yaml,
        }