import json
import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def main():
    argument_spec=dict(
        config_file=dict(type='str', required=True),
    )
    cli.YDBD.add_arguments(argument_spec)
    cli.DsTool.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydbd_cli = cli.YDBD.from_module(module)
        ydb_dstool = cli.DsTool.from_module(module)
        rc, stdout, stderr = ydb_dstool(['box', 'list', '--format=json'])
        if rc != 0:
            result['msg'] = 'dstool command box list failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

        try:
            dstool_result = json.loads(stdout)[0]
            result_keys = ['BoxId', 'PDisks_TOTAL']
            initialized = all([key in dstool_result and dstool_result[key] > 0 for key in result_keys])
        except Exception as e:
            result['msg'] = f'unexpected dstool box list result, caught {type(e).__name__}: {e}'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

        if initialized:
            result['msg'] = 'storage already initialized'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.exit_json(**result)

        rc, stdout, stderr = ydbd_cli([
            'admin', 'blobstorage', 'config', 'init', '--yaml-file', module.params.get('config_file')
        ])
        if rc != 0:
            result['msg'] = 'blobstorage config init failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)
        
        # Check PDisk status
        rc, stdout, stderr = ydb_dstool(['pdisk', 'list', '--format=json'])
        if rc == 0:
            dstool_result = json.loads(stdout)[0]
            for pdisk in dstool_result:
                if pdisk["Status"] != "ACTIVE":
                    rc = ydb_dstool(['pdisk', 'set', '--status=ACTIVE','--pdisk-ids',pdisk["NodeId:PDiskId"]])

        result['changed'] = True
        result['msg'] = 'blobstorage config init succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
