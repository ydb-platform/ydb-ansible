import time

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

        # Variables to track last attempt output
        last_rc = None
        last_stdout = None
        last_stderr = None

        while time.time() < end_ts:
            rc, stdout, stderr = ydb_cli(['discovery', 'list'])
            last_rc, last_stdout, last_stderr = rc, stdout, stderr
            if rc == 0:
                result['msg'] = 'ydb discovery is working'
                module.exit_json(**result)
            time.sleep(1)
        else:
            # Build detailed failure message with last attempt output
            failure_msg = 'ydb discovery not answered in time'
            if last_rc is not None:
                failure_msg += f'. Last attempt: rc={last_rc}, stdout="{last_stdout}", stderr="{last_stderr}"'
            result['msg'] = failure_msg
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
