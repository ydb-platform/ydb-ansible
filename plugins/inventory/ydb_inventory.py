from ansible.plugins.inventory import BaseInventoryPlugin
import yaml
import copy
from ansible.errors import AnsibleError
# from ansible.template import Templar

DOCUMENTATION = r'''
    name: ydb_inventory
    plugin_type: inventory
    short_description: YDB inventory from config.yaml
    description: |
        This inventory plugin fetches hosts from a custom source (config.yaml).
    options:
        plugin:
            description: The name of the plugin (must be 'ydb_inventory')
            required: true
            choices: ['ydb_platform.ydb.ydb_inventory']
        ydb_config:
            description: YDB config (file or dictionary)
            required: true
            env:
              - name: INVENTORY_YDB_CONFIG
'''

class InventoryModule(BaseInventoryPlugin):
    NAME = 'ydb_inventory'

    def verify_file(self, path):
        # Проверяем, что это конфиг для нашего плагина
        valid = super().verify_file(path)
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        # Загружаем конфиг плагина (YAML-файл)
        config = self._read_config_data(path)

        ydb_config = config.get('ydb_config')
        print(f"Reading inventory from {ydb_config}")

        group = 'ydb'
        self.inventory.add_group(group)

        ydb_vars = self.inventory.groups['ydb'].get_vars()
        try:
            with open(ydb_config, "r") as file:
                yaml_config = yaml.safe_load(file)
                self.inventory.groups['ydb'].set_variable('ydb_config_dict', yaml_config)
                if 'config' in yaml_config and 'self_management_config' in yaml_config['config']:
                    if 'enabled' in yaml_config['config']['self_management_config'] and yaml_config['config']['self_management_config']['enabled']:
                        self.inventory.groups['ydb'].set_variable('ydb_config_v2', True)
                # Read drives config
                drive_configs = {}
                drive_labels = {}
                if 'ydb_disks' in ydb_vars:
                    for disk in ydb_vars['ydb_disks']:
                        drive_labels[disk['label']] = disk['name']
                if 'config' in yaml_config and 'host_configs' in yaml_config['config']:
                    for drive_config in yaml_config['config']['host_configs']:
                        for i, item in enumerate(drive_config['drive']):
                            label = item['path'].split('/')[-1]
                            drive_configs[drive_config['host_config_id']] = copy.deepcopy(drive_config['drive'])
                            drive_configs[drive_config['host_config_id']][i]['label'] = label
                            if label in drive_labels:
                                drive_configs[drive_config['host_config_id']][i]['name']  = drive_labels[label]
                            else:
                                raise AnsibleError(f"Config parsing error, unable to find disk for label: {label}")
                # Read hosts and define variables for them
                if 'config' in yaml_config and 'hosts' in yaml_config['config']:
                    for host in yaml_config['config']['hosts']:
                        self.inventory.add_host(host['host'], group=group)
                        # Set variables for hosts
                        for key, value in host.items():
                            if key == 'host_config_id':
                                self.inventory.set_variable(host['host'], 'ydb_disks', drive_configs[value])
                            else:
                                self.inventory.set_variable(host['host'], key, value)
                
        except Exception as e:
            raise AnsibleError(f"Config parsing error: {str(e)}")


