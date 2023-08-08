import time
import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli



def main():
    argument_spec=dict(
        timeout=dict(type='int', default=180),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module)
        end_ts = time.time() + module.params.get('timeout')
        while time.time() < end_ts:
            rc, stdout, stderr = ydb_cli(['monitoring', 'healthcheck', '--format', 'json'])
            if rc != 0:
                module.log(f'healthcheck failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                time.sleep(5)
                continue
            try:
                data = json.loads(stdout)
                self_check_result = data['self_check_result']
            except (ValueError, KeyError):
                module.log(f'failed to parse healthcheck output {stdout}')
                time.sleep(5)
                continue
            if self_check_result != "GOOD":
                module.log(f'self check result: {self_check_result}')
                time.sleep(5)
                continue
            result['msg'] = 'ydb healthcheck result "GOOD"'
            module.exit_json(**result)

        else:
            result['msg'] = 'ydb healthcheck result did not switch to "GOOD" in time'
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
