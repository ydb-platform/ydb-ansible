import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import drive


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            label=dict(type='str', required=True),
        ),
        supports_check_mode=False,
    )
    result = {
        'changed': False,
    }
    try:
        name = module.params.get('name')
        label = module.params.get('label')

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
            result['msg'] = 'label must be valid linux file name string'
            module.fail_json(**result)
            return

        result['changed'] = drive.create_partition_if_not_exists(module, name, label)

        raise NotImplementedError()

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
