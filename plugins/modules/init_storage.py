import os


from ansible.module_utils.basic import AnsibleModule
from project.collections.ansible_collections.ydb_platform.ydb.plugins.module_utils import ydbd_cli


STORAGE_NOT_INITIALIZED_STRING = '''
Status {
  Success: true
}
Success: true
'''.strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            config_file=dict(type='str', required=True),
            ca_file=dict(type='str', default=None),
            endpoint=dict(type='str', default=None),
            token=dict(type='str', default=None, no_log=True),
            token_file=dict(type='str', default=None),
        ),
        supports_check_mode=False,
    )
    result = {
        'changed': False,
    }
    try:
        ydbd_cli = ydbd_cli.YDBDCLI(
            module=module,
            ydbd_bin='/opt/ydb/bin/ydbd',
            ca_file=module.params.get('ca_file'),
            endpoint=module.params.get('endpoint'),
            token=module.params.get('token'),
            token_file=module.params.get('token_file'),
        )
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
            return

        rc, stdout, stderr = ydbd_cli([
            'admin', 'blobstorage', 'config', 'init', '--yaml-file', module.params.get('config')
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
        return

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
