import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


STORAGE_NOT_INITIALIZED_STRING = '''
Status {
  Success: true
}
Success: true
'''.strip()


def main():
    argument_spec=dict(
        config_file=dict(type='str', required=True),

    )
    cli.YDBD.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydbd_cli = cli.YDBD.from_module(module)
        rc, stdout, stderr = ydbd_cli([
            'admin', 'blobstorage', 'config', 'invoke', '--proto', 'Command { ReadHostConfig {} }',
        ])
        if rc != 0:
            result['msg'] = 'blobstorage command ReadHostConfig failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

        initialized = stdout.strip() != STORAGE_NOT_INITIALIZED_STRING
        if initialized:
            result['msg'] = 'storage already initialized'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.exit_json(**result)

        rc, stdout, stderr = ydbd_cli([
            'admin', 'blobstorage', 'config', 'init', '--yaml-file', module.params.get('config_file')
        ])
        if rc != 0:
            result['msg'] = 'blobstorage config init failed'
            result['stdout'] = stdout
            result['stderr'] = stderr
            module.fail_json(**result)

        result['changed'] = True
        result['msg'] = 'blobstorage config init succeeded'
        result['stdout'] = stdout
        result['stderr'] = stderr
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
