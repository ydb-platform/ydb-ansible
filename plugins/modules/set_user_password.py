import re
import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def validate_user(value):
    return re.fullmatch('[a-z0-9]+', value) is not None


def normalize_password(value):
    return json.dumps(value)


def main():
    argument_spec=dict(
        new_password=dict(type='str', default=None, no_log=True),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)

    user = module.params.get('user')
    if not validate_user(user):
        result['msg'] = f'user value is invalid, may contain only lowercase Latin letters and digits'
        module.fail_json(**result)

    new_password = normalize_password(module.params.get('new_password'))

    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module, user=None, password=None)
        rc, stdout, stderr = ydb_cli(['yql', '-s', f'DECLARE $password AS Utf8; ALTER USER {user} PASSWORD {new_password};'])
        if rc == 0:
            result['msg'] = 'user password set successfully'
            module.exit_json(**result)
        else:
            module.log(f'user password set failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
            result['msg'] = f'user password set failed, see details in ansible logs on host'
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
