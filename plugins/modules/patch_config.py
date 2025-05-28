import yaml
import tempfile
import os

from ansible.module_utils.basic import AnsibleModule

def _ensure_config_path(config, path, default_value):
    """Helper function to ensure a nested config path exists with a default value."""
    current = config
    keys = path.split('.')

    # Navigate to the parent of the final key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final key if it doesn't exist
    final_key = keys[-1]
    if final_key not in current:
        current[final_key] = default_value


def patch_config_v2(config):
    _ensure_config_path(config, 'yaml_config_enabled', True)
    _ensure_config_path(config, 'self_management_config.enabled', True)
    _ensure_config_path(config, 'actor_system_config.use_auto_config', True)

    return config

def main():
    argument_spec = dict(
        config=dict(type='raw', required=True),
        output_file=dict(type='str', required=False),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = {'changed': False}

    try:
        config_input = module.params.get('config')
        output_file = module.params.get('output_file')

        # Handle different input types
        if isinstance(config_input, dict):
            # Config is already a dictionary
            config = config_input
        elif isinstance(config_input, str):
            # Config is a file path or YAML string
            if os.path.exists(config_input):
                # It's a file path
                with open(config_input, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                # It's a YAML string
                config = yaml.safe_load(config_input)
        else:
            result['msg'] = 'config must be a dictionary, file path, or YAML string'
            module.fail_json(**result)


        # Apply the patch to the config section only
        if 'config' in config:
            config['config'] = patch_config_v2(config['config'])
        else:
            config = patch_config_v2(config)


        result['changed'] = True
        result['config'] = config

        # Write to output file if specified
        if output_file and not module.check_mode:
            with open(output_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            result['msg'] = f'patched configuration written to {output_file}'
        else:
            result['msg'] = 'configuration patched successfully'

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()