from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli


INVALID_PASSWORD = 'Invalid password'


def main():
    argument_spec=dict(
        fallback_to_default_user=dict(type='bool', default=True),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module)
        rc, stdout, stderr = ydb_cli(['auth', 'get-token', '-f'])
        if rc != 0 and INVALID_PASSWORD in stderr and module.params.get('fallback_to_default_user'):
            module.log('falling back to default user')
            ydb_cli = cli.YDB.from_module(module, user='root', password='')
            rc, stdout, stderr = ydb_cli(['auth', 'get-token', '-f'])

        if rc != 0:
            result['msg'] = f'command: "ydb auth get-token" failed'
            result['stderr'] = stderr
            module.fail_json(**result)

        module.no_log_values.add('token')
        token = stdout.strip()
        result['msg'] = 'command: "ydb auth get-token" succeeded'
        result['token'] = token
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
