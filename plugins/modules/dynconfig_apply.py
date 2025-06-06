from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli


def main():
    argument_spec=dict(
        config=dict(type='str', default=""),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    configFilename     = module.params.get('config')
    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module)
        rc, stdout, stderr = ydb_cli(['admin', 'config', 'replace','-f',configFilename])
        if rc != 0:
            result['msg'] = f'command: "ydb admin config replace" failed'
            result['stderr'] = stderr
            module.fail_json(**result)

        result['msg'] = 'command: "ydb admin config replace" succeeded'
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
