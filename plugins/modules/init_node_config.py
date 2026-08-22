import json
from logging import basicConfig
import os
import shutil
import tempfile
import yaml


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump

DOCUMENTATION = r'''
    name: init_node_config
    plugin_type: module
    short_description: Create init config for a node
    description: |
        Create initial config for a node with V2 configuration
'''

def prepare_node_config(config_file):
    """Read a config file and add metadata required by node config init."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    config['metadata'] = {
        'kind': 'MainConfig',
        'cluster': '',
        'version': 0
    }
    return config


def dump_config(config):
    return yaml.safe_dump(config, default_flow_style=False, sort_keys=True)


def check_node_config_current(config_file, config_dir, result):
    """Check if node configuration already matches the requested config."""
    config_path = os.path.join(config_dir, 'config.yaml')
    if not os.path.exists(config_path):
        return False

    desired_config = prepare_node_config(config_file)
    try:
        with open(config_path, 'r') as f:
            current_config = yaml.safe_load(f)
    except Exception as e:
        result['msg'] = f'failed to read existing node configuration: {e}'
        return False

    if dump_config(current_config) == dump_config(desired_config):
        result['msg'] = 'node configuration already exists'
        return True

    result['msg'] = 'node configuration exists but differs from requested config'
    return False


def init_node_config(ydb_cli, config_file, config_dir, result):
    """Initialize node configuration using YDB configuration V2 (node init only)"""

    temp_file = None
    try:
        original_config = prepare_node_config(config_file)

        # Create temporary file
        temp_fd, temp_file = tempfile.mkstemp(suffix='.yaml', text=True)
        try:
            with os.fdopen(temp_fd, 'w') as f:
                safe_dump(original_config, f)
        except:
            os.close(temp_fd)
            raise

        # Run node init with config directory using the temporary file
        rc, stdout, stderr = ydb_cli([
            '--assume-yes', 'admin', 'node', 'config', 'init', '--config-dir', config_dir, '--from-config', temp_file
        ])

        if rc != 0:
            result['msg'] = 'node init failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            return False

        result['msg'] = 'node init succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return True

    finally:
        # Ensure temporary file is removed regardless of the result
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)


def main():
    argument_spec=dict(
        config_file=dict(type='str', required=True),
        config_dir=dict(type='str', required=True),
    )
    cli.YDB.add_arguments(argument_spec)
    # Override database requirement since node init doesn't need it
    argument_spec['database'] = dict(type='str', required=False, default='/')
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}

    try:
        ydb_cli = cli.YDB.from_module(module)
        config_file = module.params.get('config_file')
        config_dir = module.params.get('config_dir')

        config_path = os.path.join(config_dir, 'config.yaml')
        backup_path = config_path + '.ansible.bak'

        # Check if node configuration already matches the requested config
        if check_node_config_current(config_file, config_dir, result):
            module.exit_json(**result)

        if os.path.exists(config_path):
            shutil.move(config_path, backup_path)

        # Initialize node configuration
        success = init_node_config(ydb_cli, config_file, config_dir, result)

        if not success:
            if os.path.exists(backup_path):
                shutil.move(backup_path, config_path)
            module.fail_json(**result)

        if os.path.exists(backup_path):
            os.unlink(backup_path)

        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
