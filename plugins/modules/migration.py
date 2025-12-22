from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
    name: migration
    plugin_type: module
    short_description: Manipulations with configs for migration
    description: |
        Migration from V1 to V2
        Migration from V2 to V1
'''

def main():
    argument_spec=dict(
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    module.exit_json(**result)

if __name__ == '__main__':
    main()
