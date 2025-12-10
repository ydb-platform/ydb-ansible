import tempfile
import os
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump, safe_load

DOCUMENTATION = r'''
    name: cluster_config
    plugin_type: module
    short_description: Work with ydb cluster config
    description: |
        Work with ydb cluster config (it's needed for V2 cluster configuration)
'''

def fetch_cluster_config(ydb_cli, result):
    """Fetch current cluster configuration from YDB"""
    command = ['admin', 'cluster', 'config', 'fetch']
    rc, stdout, stderr = ydb_cli(command)
    if rc != 0:
        result['msg'] = 'cluster config fetch failed'
        result['stdout'] = stdout
        result['stderr'] = stderr
        result['command'] = ' '.join(ydb_cli.common_options + command)
        return None, True  # None for config, True for should_fail

    try:
        # Parse the YAML configuration
        config = safe_load(stdout)
        return config, False
    except yaml.YAMLError as e:
        result['msg'] = f'failed to parse cluster config YAML: {e}'
        result['stdout'] = stdout
        result['stderr'] = stderr
        result['command'] = ' '.join(ydb_cli.common_options + command)
        return None, True


def replace_cluster_config(ydb_cli, config_file, result):
    """Replace cluster configuration in YDB"""
    command = ['--assume-yes', 'admin', 'cluster', 'config', 'replace', '-f', config_file]
    rc, stdout, stderr = ydb_cli(command)
    if rc != 0:
        result['msg'] = 'cluster config replace failed'
        result['stdout'] = stdout
        result['stderr'] = stderr
        result['command'] = ' '.join(ydb_cli.common_options + command)
        return False

    result['msg'] = 'cluster config replace succeeded'
    result['stdout'] = stdout
    result['stderr'] = stderr
    return True


def configs_different(current_config, new_config):
    """Compare two configurations, ignoring metadata version"""
    # Handle V2 configuration format with metadata and config sections
    current_config_copy = current_config.copy() if current_config else {}
    new_config_copy = new_config.copy() if new_config else {}

    if 'metadata' in current_config_copy:
        current_config_copy.pop('metadata', None)
    if 'metadata' in new_config_copy:
        new_config_copy.pop('metadata', None)

    return current_config_copy != new_config_copy


def main():
    argument_spec = dict(
        config_file = dict(type='str', required=False),
        mode        = dict(type='str', default='replace', choices=['replace', 'fetch','load']),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = {'changed': False}

    try:
        ydb_cli     = cli.YDB.from_module(module)
        config_file = module.params.get('config_file')
        mode        = module.params.get('mode')

        if mode == 'load':
            with open(config_file, 'r') as f:
                try:
                    local_config = safe_load(f)
                except yaml.YAMLError as e:
                    result['msg'] = f'failed to parse configuration file {config_file}: {e}'
                    module.fail_json(**result)
            result['msg'] = 'configuration is loaded into variable'
            result['config'] = local_config
            module.exit_json(**result)

        if mode == 'fetch':
            # Just fetch and return current configuration without writing to file
            current_config, should_fail = fetch_cluster_config(ydb_cli, result)
            if should_fail:
                module.fail_json(**result)

            result['msg'] = 'cluster configuration retrieved'
            result['config'] = current_config
            if 'metadata' in current_config:
                result['metadata'] = current_config['metadata']
            module.exit_json(**result)

        # For 'replace' mode, config_file is required
        if not config_file:
            result['msg'] = 'config_file is required when mode is replace'
            module.fail_json(**result)

        # Load new configuration from file (from Ansible machine)
        if not os.path.exists(config_file):
            result['msg'] = f'configuration file {config_file} does not exist'
            module.fail_json(**result)

        with open(config_file, 'r') as f:
            try:
                local_config = safe_load(f)
            except yaml.YAMLError as e:
                result['msg'] = f'failed to parse configuration file {config_file}: {e}'
                module.fail_json(**result)

        # Fetch current configuration from cluster for comparison
        cluster_config, should_fail = fetch_cluster_config(ydb_cli, result)
        if should_fail:
            module.fail_json(**result)

        # Ensure the configuration has the correct structure for V2
        if 'metadata' in local_config and not 'config' in local_config:
            # If we have metadata but no config key, wrap the config in a config key
            config_without_metadata = {k: v for k, v in local_config.items() if k != 'metadata'}
            merged_config = {
                'metadata': local_config['metadata'],
                'config': config_without_metadata
            }
        else:
            # Configuration already has the correct structure or no metadata
            merged_config = local_config

        # Add config to the result
        result['metadata'] = merged_config.get('metadata', {})

        # Check if configuration needs to be updated
        if configs_different(cluster_config, merged_config):
            result['changed'] = True

            if not module.check_mode:
                # Create temporary file with merged config on the target machine
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                    safe_dump(merged_config, temp_file)
                    temp_config_file = temp_file.name

                try:
                    # Apply merged configuration
                    success = replace_cluster_config(ydb_cli, temp_config_file, result)
                    if not success:
                        module.fail_json(**result)
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_config_file):
                        os.unlink(temp_config_file)
            else:
                result['msg'] = 'configuration would be updated (check mode)'
        else:
            result['msg'] = 'configuration is already up to date'

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()