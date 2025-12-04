import os


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import drive, cli

DOCUMENTATION = r'''
    name: dstool_cmd
    plugin_type: module
    short_description: YDB DSTool command executor
    description: |
        Module for running commands with YDB DSTool
'''

def main():
    argument_spec = dict(
        cmd=dict(type='str', default='')
    )
    cli.DsTool.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        
        ydbd_cli = cli.DsTool.from_module(module)
        cmd = module.params.get('cmd')

        rc,stdout,stderr = ydbd_cli(cmd.split(" "))
        result['stdout'] = stdout
        if rc != 0:
            result['stderr'] = stderr
            module.fail_json(**result)
        result['changed'] = True

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
