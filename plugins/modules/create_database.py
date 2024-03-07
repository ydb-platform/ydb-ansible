from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


STDOUT_SUCCESS = 'OK'
STDOUT_ALREADY_EXISTS = 'ERROR: ALREADY_EXISTS'


def main():
    argument_spec=dict(
        database=dict(type='str', required=True),
        pool_kind=dict(type='str', required=True),
        groups=dict(type='int', required=True),
    )
    cli.YDBD.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        database = module.params.get('database')
        pool_kind = module.params.get('pool_kind')
        groups = module.params.get('groups')

        ydbd_cli = cli.YDBD.from_module(module)
        rc, stdout, stderr = ydbd_cli([
            'admin', 'database', database, 'create', f'{pool_kind}:{groups}',
        ])
        if rc != 0:
            result['msg'] = 'database create command failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

        if stdout.strip() == STDOUT_SUCCESS:
            result['changed'] = True
            result['msg'] = 'database create command succeeded'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.exit_json(**result)

        elif stdout.startswith(STDOUT_ALREADY_EXISTS):
            result['changed'] = False
            result['msg'] = 'database already exists'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.exit_json(**result)

        else:
            result['msg'] = 'unexpected output'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
