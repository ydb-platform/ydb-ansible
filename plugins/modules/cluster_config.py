import tempfile
import os
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli


def fetch_cluster_config(ydb_cli, result):
    """Fetch current cluster configuration from YDB"""
    rc, stdout, stderr = ydb_cli(['admin', 'cluster', 'config', 'fetch'])
    if rc != 0:
        result['msg'] = 'cluster config fetch failed'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return None, True  # None for config, True for should_fail

    try:
        # Parse the YAML configuration
        config = yaml.safe_load(stdout)
        return config, False
    except yaml.YAMLError as e:
        result['msg'] = f'failed to parse cluster config YAML: {e}'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return None, True


def replace_cluster_config(ydb_cli, config_file, result):
    """Replace cluster configuration in YDB"""
    rc, stdout, stderr = ydb_cli(['--assume-yes', 'admin', 'cluster', 'config', 'replace', '-f', config_file])
    if rc != 0:
        result['msg'] = 'cluster config replace failed'
        result['stdout'] = stdout
        result['stderr'] = stderr
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

    if 'config' in current_config_copy:
        current_config_copy = current_config_copy['config']
    if 'config' in new_config_copy:
        new_config_copy = new_config_copy['config']

    if 'metadata' in current_config_copy:
        current_config_copy.pop('metadata', None)
    if 'metadata' in new_config_copy:
        new_config_copy.pop('metadata', None)

    return current_config_copy != new_config_copy


def main():
    argument_spec = dict(
        config_file=dict(type='str', required=False),
        state=dict(type='str', default='present', choices=['present', 'fetch', 'get']),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = {'changed': False}

    try:
        ydb_cli = cli.YDB.from_module(module)
        config_file = module.params.get('config_file')
        state = module.params.get('state')

        # Validate config_file is provided when needed
        if state in ['present', 'fetch'] and not config_file:
            result['msg'] = f'config_file is required when state is {state}'
            module.fail_json(**result)

        if state == 'fetch':
            # Just fetch and return current configuration
            current_config, should_fail = fetch_cluster_config(ydb_cli, result)
            if should_fail:
                module.fail_json(**result)

            # Write current config to file
            with open(config_file, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False)

            result['msg'] = f'cluster configuration fetched and saved to {config_file}'
            result['config'] = current_config
            module.exit_json(**result)

        elif state == 'get':
            # Just fetch and return current configuration without writing to file
            current_config, should_fail = fetch_cluster_config(ydb_cli, result)
            if should_fail:
                module.fail_json(**result)

            result['msg'] = 'cluster configuration retrieved'
            result['config'] = current_config
            if 'metadata' in current_config:
                result['metadata'] = current_config['metadata']
            module.exit_json(**result)

        elif state == 'present':
            # Load new configuration from file (from Ansible machine)
            if not os.path.exists(config_file):
                result['msg'] = f'configuration file {config_file} does not exist'
                module.fail_json(**result)

            with open(config_file, 'r') as f:
                try:
                    local_config = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    result['msg'] = f'failed to parse configuration file {config_file}: {e}'
                    module.fail_json(**result)

            # Fetch current configuration from cluster for comparison
            cluster_config, should_fail = fetch_cluster_config(ydb_cli, result)
            if should_fail:
                module.fail_json(**result)

            # The local_config is already properly formatted with metadata and config sections
            # by the playbook, so we can use it directly
            merged_config = local_config

            # Check if configuration needs to be updated
            if configs_different(cluster_config, merged_config):
                result['changed'] = True

                if not module.check_mode:
                    # Create temporary file with merged config on the target machine
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                        yaml.dump(merged_config, temp_file, default_flow_style=False)
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