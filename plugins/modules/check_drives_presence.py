from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
    name: check_drives_presence
    plugin_type: module
    short_description: Check presence of drives on hosts
    description: |
        This plugins check that YDB Config drives are described in Ansible config and they present on a host
'''

def run_module():
    module_args = dict(
        ydb_drives=dict(type='list', required=True),
        ydb_disks=dict(type='list', required=True),
        host_drives=dict(type='list', required=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
    )

    ydb_drives = module.params['ydb_drives']
    ydb_disks = module.params['ydb_disks']
    host_drives = module.params['host_drives']

    errors = []
    ydb_disks_labels = {disk['label']: disk['name'] for disk in ydb_disks}
    host_drives_set = set(host_drives)
    for drive in ydb_drives:
        label = drive.get('label')
        if not label:
            errors.append("Drive must have a 'label' field.")
            continue

        if label not in ydb_disks_labels:
            errors.append(f"Label '{label}' is not found in ydb_disks.")
            continue

        name = ydb_disks_labels[label]
        device_name = name.split('/')[-1]  # Extract device name like 'vdb'

        if device_name not in host_drives_set:
            errors.append(f"Device '{device_name}' is not found in host_drives.")

    result['changed'] = False
    if errors:
            module.fail_json(msg="There are problems with drives: " + ",".join(errors))

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()