import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import drive, cli

DOCUMENTATION = r'''
    name: ydbd_cmd
    plugin_type: module
    short_description: YDBD command executor
    description: |
        Module for running commands with YDBD
'''

def main():
    argument_spec = dict(
        cmd=dict(type='str', default='')
    )
    cli.YDBD.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        
        ydbd_cli = cli.YDBD.from_module(module)
        cmd = module.params.get('cmd')

        rc,stdout,_ = ydbd_cli(cmd.split(" "))
        result['stdout'] = stdout
        result['changed'] = True

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
