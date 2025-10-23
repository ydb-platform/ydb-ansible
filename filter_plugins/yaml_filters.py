import os
import sys
import importlib.util
from ansible.utils.display import Display

from ansible_collections.ydb_platform.ydb.plugins.filter.yaml_filters import ydb_config_to_yaml, FilterModule as OrigFilterModule

DOCUMENTATION = r'''
    name: yaml_filters
    plugin_type: filter
    short_description: short desc
    description: |
        long description
'''

class FilterModule(object):
    """
    Re-export the ydb_config_to_yaml filter for Ansible
    """

    def filters(self):
        Display().vvv("Registering ydb_config_to_yaml filter from filter_plugins directory")
        return {
            'ydb_config_to_yaml': ydb_config_to_yaml,
        }