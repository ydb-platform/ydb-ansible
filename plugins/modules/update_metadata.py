import os
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump, safe_load

DOCUMENTATION = r'''
    name: update_metadata
    plugin_type: module
    short_description: Update metadata in YDB config
    description: |
        Update metadata in YDB config
'''

def run_module():
    module_args = dict(
        config=dict(type='raw', required=True),
        current_metadata=dict(type='dict', required=False),
        output_file=dict(type='str', required=False),
    )

    result = dict(
        changed=False,
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    config_input = module.params['config']
    current_metadata = module.params.get('current_metadata')
    output_file = module.params.get('output_file')

    # Determine if config is a file path or a dictionary
    if isinstance(config_input, str):
        # Check if config file exists
        if not os.path.exists(config_input):
            module.fail_json(msg=f'Config file {config_input} does not exist')

        # Load YAML config
        try:
            with open(config_input, 'r') as f:
                config = safe_load(f)
        except Exception as e:
            module.fail_json(msg=f'Failed to parse YAML: {str(e)}')

        # Use the input path as output if not specified
        if not output_file:
            output_file = config_input
    else:
        # Assume it's a dictionary
        config = config_input

    # Ensure config is a dictionary
    if not isinstance(config, dict):
        module.fail_json(msg='Config must be a valid dictionary')

    # Initialize metadata if not present
    if 'metadata' not in config:
        if current_metadata:
            config['metadata'] = current_metadata.copy()
        else:
            config['metadata'] = {}
        result['changed'] = True

    # Handle version increment
    if 'version' not in config['metadata']:
        # If no version in metadata, set it to 1 or use from current_metadata
        if current_metadata and 'version' in current_metadata:
            try:
                current_version = int(current_metadata['version'])
                config['metadata']['version'] = current_version
                result['changed'] = True
            except (ValueError, TypeError):
                module.fail_json(msg='Version in current_metadata must be an integer')
        else:
            config['metadata']['version'] = 1
            result['changed'] = True
    else:
        try:
            current_version = int(current_metadata['version'])
            config['metadata']['version'] = current_version
            result['changed'] = True
        except (ValueError, TypeError):
            module.fail_json(msg='Version in metadata must be an integer')

    # Write the updated config if output_file is specified and changes were made
    if output_file and result['changed'] and not module.check_mode:
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