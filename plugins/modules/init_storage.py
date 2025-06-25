import json
import re
import yaml
import uuid


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def check_storage_initialization(ydb_dstool, result):
    """Check if storage is already initialized using dstool"""
    rc, stdout, stderr = ydb_dstool(['box', 'list', '--format=json'])
    if rc != 0:
        # If dstool box list fails, assume storage is not initialized
        return False, False

    try:
        dstool_result = json.loads(stdout)[0]
        result_keys = ['BoxId', 'PDisks_TOTAL']
        initialized = all([key in dstool_result and dstool_result[key] > 0 for key in result_keys])
        return initialized, False
    except Exception as e:
        # If we can't parse the result, fail
        return False, True


def set_pdisk_active_status(ydb_dstool):
    """Set PDisk status to ACTIVE for any inactive PDisks"""
    rc, stdout, stderr = ydb_dstool(['pdisk', 'list', '--format=json'])
    if rc == 0:
        try:
            dstool_result = json.loads(stdout)
            for pdisk in dstool_result:
                if "Status" in pdisk and pdisk["Status"] != "ACTIVE":
                    ydb_dstool(['pdisk', 'set', '--status=ACTIVE', '--pdisk-ids', pdisk["NodeId:PDiskId"]])
        except Exception:
            # Ignore errors in PDisk status setting as it's not critical
            pass


def init_storage_using_config_v1(ydbd_cli, config_file, result, update_config):
    """Initialize storage using YDB configuration V1 (blobstorage config init)"""
    cmd = ['admin', 'blobstorage', 'config', 'init', '--yaml-file', config_file]
    rc, stdout, stderr = ydbd_cli(cmd)
    if rc != 0:
        result['msg'] = 'blobstorage config init failed'
        if update_config:
                # Detect required config generation
                pattern = r'ItemConfigGenerationExpected: (\d+)'
                match = re.search(pattern, stdout)
                if match:
                    expected_value = int(match.group(1))
                    # Replace current generation in config
                    with open(config_file, 'r') as file:
                        data = yaml.safe_load(file)
                    if data is not None:
                        if 'storage_config_generation' in data:
                            data['storage_config_generation'] = expected_value
                            new_config_file = config_file + '-ansible'
                            with open(new_config_file, 'w') as file:
                                yaml.dump(data, file, default_flow_style=False)
                                rc, stdout, stderr = ydbd_cli([
                                    'admin', 'blobstorage', 'config', 'init', '--yaml-file', new_config_file
                                ])
                                if rc != 0:
                                    result['msg'] = f"blobstorage config init failed with expected config"
                                else:
                                    result['msg'] = 'blobstorage config init succeeded'
                                    result['stdout'] = stdout
                                    result['stderr'] = stderr
                                    return True
                    else:
                        result['msg'] = f"blobstorage config init failed, Expected value of ItemConfigGenerationExpected: {expected_value}"
                else:
                    result['msg'] = f"blobstorage config init failed, Expected value was not found"
        if rc != 0:
            result['cmd'] = ' '.join(ydbd_cli.common_options + cmd)
            result['stdout'] = stdout
            result['stderr'] = stderr
            return False
    else:
        result['msg'] = 'blobstorage config init succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return True


def init_storage_using_config_v2(ydb_cli, result):
    """Initialize storage using YDB configuration V2 (bootstrap only)"""

    # ydb_cli = cli.YDB.from_module(ydb_cli_with_db.module)

    # Run bootstrap with config directory (node init should have been done before ydbd start)
    cmd = ['--assume-yes', 'admin', 'cluster', 'bootstrap', '--uuid', str(uuid.uuid4())]
    rc, stdout, stderr = ydb_cli(cmd)
    if rc != 0:
        result['msg'] = 'bootstrap failed'
        result['cmd'] = ' '.join(ydb_cli.common_options + cmd)
        result['stdout'] = stdout
        result['stderr'] = stderr
        return False
    else:
        result['msg'] = 'bootstrap succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return True


def main():
    argument_spec=dict(
        config_file=dict(type='str', required=True),
        update_config=dict(type='bool', default=False),
        use_config_v2=dict(type='bool', default=False),
    )
    cli.YDBD.add_arguments(argument_spec)
    cli.YDB.add_arguments(argument_spec)
    cli.DsTool.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}

    try:
        ydbd_cli = cli.YDBD.from_module(module)
        ydb_cli = cli.YDB.from_module(module)
        ydb_dstool = cli.DsTool.from_module(module)
        config_file = module.params.get('config_file')
        use_config_v2 = module.params.get('use_config_v2')
        update_config = module.params.get('update_config')

        initialized, should_fail = check_storage_initialization(ydb_dstool, result)

        if should_fail:
            result['msg'] = 'Failed to parse storage initialization status'
            module.fail_json(**result)

        if initialized and not update_config:
            result['msg'] = 'storage already initialized'
            module.exit_json(**result)

        # Initialize storage using the appropriate method
        if use_config_v2:
            success = init_storage_using_config_v2(ydb_cli, result)
        else:
            success = init_storage_using_config_v1(ydbd_cli, config_file, result, update_config)

        if not success:
            module.fail_json(**result)

        # Set PDisk status to ACTIVE if needed
        set_pdisk_active_status(ydb_dstool)

        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()