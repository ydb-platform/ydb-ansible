from ansible.plugins.inventory import BaseInventoryPlugin
import copy
from ansible.errors import AnsibleError
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump, safe_load

DOCUMENTATION = r'''
    name: ydb_inventory
    plugin_type: inventory
    short_description: Get YDB inventory from config.yaml
    description: |
        This inventory plugin fetches hosts from a custom source (config.yaml).
    options:
        plugin:
            description: The name of the plugin (it should always be set to 'ydb_platform.ydb.ydb_inventory')
            required: true
            type: str
            choices: ['ydb_platform.ydb.ydb_inventory']
        ydb_config:
            description: YDB config (file or dictionary)
            required: true
            type: str
            env:
              - name: INVENTORY_YDB_CONFIG
        ydb_hostgroup_name:
            description: The name of group of hosts
            required: false
            default: 'ydb'
            env:
              - name: INVENTORY_YDB_HOSTGROUP_NAME
'''

class InventoryModule(BaseInventoryPlugin):
    NAME = 'ydb_inventory'

    def verify_file(self, path):
        # Проверяем, что это конфиг для нашего плагина
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('ydb_inventory.yaml', 'ydb_inventory.yml', 'inventory.yaml', 'inventory.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        # Загружаем конфиг плагина (YAML-файл)
        config = self._read_config_data(path)

        ydb_config = config.get('ydb_config')
        print(f"Reading inventory from {ydb_config}")

        group_name = config.get('ydb_hostgroup_name','ydb')
        self.inventory.add_group(group_name)
        brokers = []

        try:
            with open(ydb_config, "r") as file:
                yaml_config = safe_load(file)

                self.inventory.groups[group_name].set_variable('ydb_config_dict', yaml_config)

                if 'config' in yaml_config:
                    """ V2 Config """
                    yaml_config = yaml_config['config']

                ydb_enforce_user_token_requirement = yaml_config.get('domains_config', {}).get('security_config', {}).get('enforce_user_token_requirement', False)
                self.inventory.groups[group_name].set_variable('ydb_enforce_user_token_requirement', ydb_enforce_user_token_requirement)

                if 'default_disk_type' in yaml_config:
                    self.inventory.groups[group_name].set_variable('ydb_pool_kind', yaml_config['default_disk_type'].lower())
                if 'domains_config' in yaml_config and 'domain' in yaml_config['domains_config']:
                    if 'storage_pool_types' in yaml_config['domains_config']['domain'][0]:
                        self.inventory.groups[group_name].set_variable('ydb_pool_kind', yaml_config['domains_config']['domain'][0]['storage_pool_types'][0]['kind'])

                if 'self_management_config' in yaml_config and 'enabled' in yaml_config['self_management_config'] and yaml_config['self_management_config']['enabled']:
                    self.inventory.groups[group_name].set_variable('ydb_config_v2', True)

                self.inventory.groups[group_name].set_variable('ydb_config', yaml_config)

                domain = 'Root'
                if 'domains_config' in yaml_config and 'domain' in yaml_config['domains_config']:
                    domain = yaml_config['domains_config']['domain'][0]['name']
                self.inventory.groups[group_name].set_variable('ydb_domain',domain)

                # Read drives config
                drive_configs = {}
                drive_labels = {}

                if 'host_configs' in yaml_config:
                    for drive_config in yaml_config['host_configs']:
                        drive_configs[drive_config['host_config_id']] = copy.deepcopy(drive_config['drive'])
                        for i, item in enumerate(drive_config['drive']):
                            if '/dev/disk/by-partlabel/' in item['path']:
                                label = item['path'].split('/')[-1]
                                drive_configs[drive_config['host_config_id']][i]['label'] = label
                                if label in drive_labels:
                                    drive_configs[drive_config['host_config_id']][i]['name']  = drive_labels[label]
                # Read hosts and define variables for them
                if 'hosts' in yaml_config:
                    for host in yaml_config['hosts']:
                        self.inventory.add_host(host['host'], group=group_name)
                        # Set variables for hosts
                        for key, value in host.items():
                            if key == 'host_config_id':
                                self.inventory.set_variable(host['host'], 'ydb_drives', drive_configs[value])
                            else:
                                self.inventory.set_variable(host['host'], key, value)
                        if len(brokers) < 3:
                            brokers.append(host['host'])

                self.inventory.groups[group_name].set_variable('ydb_brokers', brokers)

        except Exception as e:
            raise AnsibleError(f"Config parsing error: {str(e)}")


