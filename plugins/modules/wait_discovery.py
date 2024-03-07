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
        while time.time() < end_ts:
            rc, _, _ = ydb_cli(['discovery', 'list'])
            if rc == 0:
                result['msg'] = 'ydb discovery is working'
                module.exit_json(**result)
            time.sleep(1)
        else:
            result['msg'] = 'ydb discovery not answered in time'
            module.fail_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
