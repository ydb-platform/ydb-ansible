import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import drive, cli


def main():
    argument_spec = dict(
        name=dict(type='str', required=True),
        label=dict(type='str', required=True),
        allow_format=dict(type='bool', default=False),
        main_key=dict(type='str', default='8229298086344098676'),
    )
    cli.YDBD.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        name = module.params.get('name')
        label = module.params.get('label')
        allow_format = module.params.get('allow_format')

        if not os.path.isabs(name):
            result['msg'] = 'device name must be specified as absolute path to block device node'
            module.fail_json(**result)
            return

        if not os.path.exists(name):
            result['msg'] = f'device {name} not found'
            module.fail_json(**result)
            return

        if not drive.is_block_device(name):
            result['msg'] = f'device {name} is not block device'
            module.fail_json(**result)
            return

        if len(label) == 0:
            result['msg'] = 'label must be non-empty string'
            module.fail_json(**result)
            return

        if '/' in label:
            result['msg'] = 'label must not contain "/"'
            module.fail_json(**result)
            return


        changed, label_path = drive.create_partition_if_not_exists(module, name, label)
        result['changed'] = changed

        if changed:
            if allow_format:
                module.log(f'filling first 1M of YDB disk {label_path} with zeros')
                drive.prepare_partition_using_dd(module, label_path)
            else:
                module.log(f'filling first 1M of YDB disk {label_path} is disallowed: "allow_format" flag is False')

        ydbd_cli = cli.YDBD.from_module(module)

        rc, _, _ = ydbd_cli(['admin', 'bs', 'disk', 'info', '-k', module.params.get('main_key'), label_path])
        if rc == 0:
            module.log(f'found pre-formatted YDB disk {label_path}')
        else:
            obliterated = drive.check_if_disk_was_obliterated(module, label_path)
            if obliterated:
                module.log(f'found pre-obliterated YDB disk {label_path}')
            else:
                if allow_format:
                    module.log(f'obliterating YDB disk {label_path}')
                    rc, _, _ = ydbd_cli(['admin', 'bs', 'disk', 'obliterate', label_path])
                    result['changed'] =  True
                    if rc != 0:
                        result['msg'] = f'failed to obliterate disk {label_path}'
                        module.fail_json(**result)
                        return
                else:
                    module.log(f'obliterating YDB disk {label_path} is disallowed: "allow_format" flag is False')

        result['changed'] = changed

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
