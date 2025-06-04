import os
import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump


def run_module():
    module_args = dict(
        config=dict(type='str', required=True),
        output_file=dict(type='str', required=False),
        database_cores=dict(type='int', required=False),
        storage_cores=dict(type='int', required=False),
    )

    result = dict(
        changed=False,
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    config_path = module.params['config']
    output_file = module.params.get('output_file', config_path)
    database_cores = module.params.get('database_cores')
    storage_cores = module.params.get('storage_cores')

    # Define description constants to avoid duplication
    database_node_description = 'Actorsystem for database nodes'
    storage_node_description = 'Actorsystem for storage nodes'

    # Check if at least one core setting is provided
    if not database_cores and not storage_cores:
        module.fail_json(msg='At least one of database_cores or storage_cores must be provided')

    # Check if config file exists
    if not os.path.exists(config_path):
        module.fail_json(msg=f'Config file {config_path} does not exist')

    # Load YAML config
    try:
        with open(config_path, 'r') as f:
            config = yaml.load(f, Loader=SafeLoader)
    except Exception as e:
        module.fail_json(msg=f'Failed to parse YAML: {str(e)}')

    if not isinstance(config, dict):
        module.fail_json(msg='Config file does not contain a valid YAML dictionary')

    # Add allowed_labels section
    if 'allowed_labels' not in config:
        config['allowed_labels'] = {}
        result['changed'] = True

    if 'dynamic' not in config['allowed_labels']:
        config['allowed_labels']['dynamic'] = {'type': 'string'}
        result['changed'] = True

    # Create or update selector_config
    if 'selector_config' not in config:
        config['selector_config'] = []
        result['changed'] = True

    # Check if we need to add/update database selector
    if database_cores:
        database_selector = next((s for s in config.get('selector_config', [])
                                if s.get('description') == database_node_description), None)

        if database_selector:
            # Update existing selector
            if (database_selector.get('config', {}).get('actor_system_config', {}).get('cpu_count') != database_cores or
                database_selector.get('selector', {}).get('dynamic') is not True):
                database_selector['config']['actor_system_config']['cpu_count'] = database_cores
                database_selector['selector'] = {'dynamic': True}
                result['changed'] = True
        else:
            # Add new database selector
            config['selector_config'].append({
                'config': {
                    'actor_system_config': {
                        'cpu_count': database_cores,
                        'node_type': 'COMPUTE'
                    }
                },
                'description': database_node_description,
                'selector': {
                    'dynamic': True
                }
            })
            result['changed'] = True

    # Check if we need to add/update storage selector
    if storage_cores:
        storage_selector = next((s for s in config.get('selector_config', [])
                              if s.get('description') == storage_node_description), None)

        if storage_selector:
            # Update existing selector
            if (storage_selector.get('config', {}).get('actor_system_config', {}).get('cpu_count') != storage_cores or
                storage_selector.get('selector', {}).get('dynamic') is not False):
                storage_selector['config']['actor_system_config']['cpu_count'] = storage_cores
                storage_selector['selector'] = {'dynamic': False}
                result['changed'] = True
        else:
            # Add new storage selector
            config['selector_config'].append({
                'config': {
                    'actor_system_config': {
                        'cpu_count': storage_cores,
                        'node_type': 'STORAGE'
                    }
                },
                'description': storage_node_description,
                'selector': {
                    'dynamic': False
                }
            })
            result['changed'] = True

    # Write the updated config if changes were made
    if result['changed'] and not module.check_mode:
        try:
            with open(output_file, 'w') as f:
                safe_dump(config, f)
        except Exception as e:
            module.fail_json(msg=f'Failed to write config: {str(e)}')

    # Add the config to the result for use by other tasks
    result['config'] = config

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()