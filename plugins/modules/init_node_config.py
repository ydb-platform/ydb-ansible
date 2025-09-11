import json
from logging import basicConfig
import os
import tempfile
import yaml


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump


def check_node_config_exists(config_dir, result):
    """Check if node configuration already exists"""
    config_path = os.path.join(config_dir, 'config.yaml')
    if os.path.exists(config_path):
        result['msg'] = 'node configuration already exists'
        return True
    return False


def init_node_config(ydb_cli, config_file, config_dir, result):
    """Initialize node configuration using YDB configuration V2 (node init only)"""

    temp_file = None
    try:
        # Read the original config file
        with open(config_file, 'r') as f:
            original_config = yaml.safe_load(f)

        # Create the initial metadata structure
        original_config['metadata'] = {
            'kind': 'basicConfig',
            'cluster': '',
            'version': 0
        }

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

        # Check if node configuration already exists
        if check_node_config_exists(config_dir, result):
            module.exit_json(**result)

        # Initialize node configuration
        success = init_node_config(ydb_cli, config_file, config_dir, result)

        if not success:
            module.fail_json(**result)

        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
