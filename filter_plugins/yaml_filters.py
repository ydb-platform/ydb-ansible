import os
import sys
import importlib.util
from ansible.utils.display import Display

from ansible_collections.ydb_platform.ydb.plugins.filter.yaml_filters import custom_to_nice_yaml, FilterModule as OrigFilterModule



class FilterModule(object):
    """
    Re-export the custom_to_nice_yaml filter for Ansible
    """

    def filters(self):
        Display().vvv("Registering custom_to_nice_yaml filter from filter_plugins directory")
        return {
            'custom_to_nice_yaml': custom_to_nice_yaml,
        }