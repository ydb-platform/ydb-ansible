import json
import os
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


def init_storage_using_config_v1(ydbd_cli, config_file, result):
    """Initialize storage using YDB configuration V1 (blobstorage config init)"""
    cmd = ['admin', 'blobstorage', 'config', 'init', '--yaml-file', config_file]
    rc, stdout, stderr = ydbd_cli(cmd)
    if rc != 0:
        result['msg'] = 'blobstorage config init failed'
        result['cmd'] = ' '.join(ydbd_cli.common_options + cmd)
        result['stdout'] = stdout
        result['stderr'] = stderr
        return False
    else:
        result['msg'] = 'blobstorage config init succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        return True


def init_storage_using_config_v2(ydb_cli_with_db, result):
    """Initialize storage using YDB configuration V2 (bootstrap only)"""

    ydb_cli = cli.YDB.from_module(ydb_cli_with_db.module)

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

        initialized, should_fail = check_storage_initialization(ydb_dstool, result)

        if should_fail:
            result['msg'] = 'Failed to parse storage initialization status'
            module.fail_json(**result)

        if initialized:
            result['msg'] = 'storage already initialized'
            module.exit_json(**result)

        # Initialize storage using the appropriate method
        if use_config_v2:
            success = init_storage_using_config_v2(ydb_cli, result)
        else:
            success = init_storage_using_config_v1(ydbd_cli, config_file, result)

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