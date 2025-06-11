import time
import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli

INVALID_PASSWORD = 'CLIENT_UNAUTHENTICATED'

def main():
    argument_spec=dict(
        timeout=dict(type='int', default=180),
        enforce_user_token_requirement=dict(type='bool', default=False),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydb_cmd  = ['monitoring', 'healthcheck', '--format', 'json']
        end_ts   = time.time() + module.params.get('timeout')
        password = module.params.get('password')
        user     = module.params.get('user')
        enforce_user_token_requirement = module.params.get('enforce_user_token_requirement')
        if user != '' and password != '' and enforce_user_token_requirement == True:
            ydb_cli  = cli.YDB.from_module(module, user=user, password=password)
        else:
            # Anonymouse mode
            ydb_cli  = cli.YDB.from_module(module)

        # Variables to track last attempt output
        last_rc = None
        last_stdout = None
        last_stderr = None
        last_data = None
        last_self_check_result = None

        while time.time() < end_ts:
            rc, stdout, stderr = ydb_cli(ydb_cmd)
            last_rc, last_stdout, last_stderr = rc, stdout, stderr

            if rc != 0:
                if user != '':
                # Try to connect without password
                    ydb_cmd_nopass = ydb_cmd.copy()
                    ydb_cmd_nopass.insert(0,user)
                    ydb_cmd_nopass.insert(0,'--user')
                    ydb_cmd_nopass.insert(0,'--no-password')
                    rc, stdout, stderr = ydb_cli(ydb_cmd_nopass)
                    last_rc, last_stdout, last_stderr = rc, stdout, stderr
            if rc != 0:
                module.log(f'healthcheck failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                time.sleep(5)
                continue
            try:
                data = json.loads(stdout)
                last_data = data
                self_check_result = data['self_check_result']
                last_self_check_result = self_check_result
            except (ValueError, KeyError):
                module.log(f'failed to parse healthcheck output {stdout}')
                time.sleep(5)
                continue
            if self_check_result not in ("GOOD", "DEGRADED"):
                module.log(f'self check result: {self_check_result}: {data}')
                time.sleep(5)
                continue
            result['msg'] = f'ydb healthcheck result "{self_check_result}": {data}'
            module.exit_json(**result)

        else:
            # Build detailed failure message with last attempt output
            failure_msg = 'ydb healthcheck result did not switch to "GOOD" in time'
            if last_rc is not None:
                failure_msg += f'. Last attempt: rc={last_rc}'
                if last_rc != 0:
                    failure_msg += f', stdout="{last_stdout}", stderr="{last_stderr}"'
                elif last_data:
                    if last_self_check_result:
                        failure_msg += f', result="{last_self_check_result}", data={last_data}'
                    else:
                        failure_msg += f', stdout="{last_stdout}"'
                else:
                    failure_msg += f', stdout="{last_stdout}"'
            result['msg'] = failure_msg
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
