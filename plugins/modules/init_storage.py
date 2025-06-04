import json
import re
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def main():
    argument_spec=dict(
        config_file=dict(type='str', required=True),
        update_config=dict(type='bool', default=False)
    )
    cli.YDBD.add_arguments(argument_spec)
    cli.DsTool.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydbd_cli = cli.YDBD.from_module(module)
        ydb_dstool = cli.DsTool.from_module(module)
        rc, stdout, stderr = ydb_dstool(['box', 'list', '--format=json'])
        update_config = module.params.get('update_config')
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

        if initialized and not update_config:
            result['msg'] = 'storage already initialized'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.exit_json(**result)

        rc, stdout, stderr = ydbd_cli([
            'admin', 'blobstorage', 'config', 'init', '--yaml-file', module.params.get('config_file')
        ])
        if rc != 0:
            result['msg'] = 'blobstorage config init failed'
            if update_config:
                # Detect required config generation
                pattern = r'ItemConfigGenerationExpected: (\d+)'
                match = re.search(pattern, stdout)
                if match:
                    expected_value = int(match.group(1))
                    # Replace current generation in config
                    with open(module.params.get('config_file'), 'r') as file:
                        data = yaml.safe_load(file)
                    if data is not None:
                        if 'storage_config_generation' in data:
                            data['storage_config_generation'] = expected_value
                            new_config_file = module.params.get('config_file') + '-ansible'
                            with open(new_config_file, 'w') as file:
                                yaml.dump(data, file, default_flow_style=False)
                                rc, stdout, stderr = ydbd_cli([
                                    'admin', 'blobstorage', 'config', 'init', '--yaml-file', new_config_file
                                ])
                                if rc != 0:
                                    result['msg'] = f"blobstorage config init failed with expected config"
                    else:
                        result['msg'] = f"blobstorage config init failed, Expected value of ItemConfigGenerationExpected: {expected_value}"
                else:
                    result['msg'] = f"blobstorage config init failed, Expected value was not found"
            if rc != 0:
                result['stdout'] = stdout
                result['stderr'] = stderr
                module.fail_json(**result)
        
        # Check PDisk status
        rc, stdout, stderr = ydb_dstool(['pdisk', 'list', '--format=json'])
        if rc == 0:
            dstool_result = json.loads(stdout)
            for pdisk in dstool_result:
                if "Status" in pdisk and pdisk["Status"] != "ACTIVE":
                    rc = ydb_dstool(['pdisk', 'set', '--status=ACTIVE', '--pdisk-ids', pdisk["NodeId:PDiskId"]])

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