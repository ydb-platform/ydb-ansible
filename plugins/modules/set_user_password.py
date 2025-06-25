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
        result = {'changed': False}
        result['msg'] = f'user value is invalid, may contain only lowercase Latin letters and digits'
        module.fail_json(**result)

    new_password = normalize_password(module.params.get('new_password'))

    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module, user=None, password=None)

        # For root user, we'll assume it exists already
        user_exists = user == 'root'

        if not user_exists:
            # Try to check user existence using YQL
            rc, stdout, stderr = ydb_cli(['yql', '-s', f'SELECT * FROM `.sys/users` WHERE `name`="{user}";'])
            user_exists = rc == 0 and user in stdout
            module.log(f'User existence check result: {user_exists}, rc={rc}, stdout={stdout}')

        if not user_exists:
            module.log(f'User {user} does not exist, creating it with YQL')
            # Create user with YQL
            rc, stdout, stderr = ydb_cli(['yql', '-s', f'CREATE USER {user};'])

            if rc != 0:
                if "User already exists" in stderr:
                    module.log(f'User {user} already exists, proceeding to set password')
                else:
                    module.log(f'Failed to create user {user} using YQL: {stderr}')
                    result['msg'] = f'Failed to create user {user}: {stderr}'
                    module.fail_json(**result)
            else:
                result['changed'] = True
                result['user_created'] = True

        # Now set the password
        rc, stdout, stderr = ydb_cli(['yql', '-s', f'DECLARE $password AS Utf8; ALTER USER {user} PASSWORD {new_password};'])
        if rc == 0:
            result['changed'] = True
            result['msg'] = 'user password set successfully'
            module.exit_json(**result)
        else:
            module.log(f'user password set failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
            # Check for specific transient errors that might benefit from retries
            transient_errors = ['connection refused', 'timeout', 'temporary unavailable', 'service unavailable']
            error_lower = stderr.lower()
            if any(err in error_lower for err in transient_errors):
                result['msg'] = f'Transient error when setting user password: {stderr}'
                module.fail_json(**result)
            else:
                result['msg'] = f'user {user} set failed, see details in ansible logs on host'
                result['stderr'] = stderr
                module.fail_json(**result)

    except Exception as e:
        module.log(f'unexpected exception: {e}')
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
