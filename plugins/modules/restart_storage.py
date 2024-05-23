from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli


def main():
    argument_spec=dict(
        timeout=dict(type='int', default=180),
    )
    cli.YdbOps.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydbops_cli = cli.YdbOps.from_module(module)
        module.log(f'running {ydbops_cli.common_options}')
        rc, stdout, stderr = ydbops_cli([])
        result['msg'] = f'ydbops status — rc: {rc}, stdout: {stdout}, stderr: {stderr}'
        if rc == 0:
            module.exit_json(**result)
        else:
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
