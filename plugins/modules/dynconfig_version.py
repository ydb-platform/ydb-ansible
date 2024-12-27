import re

#
# This module returns current version of dynamic config
# The result is stored in 'version' variable of returning dict

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
        ydb_cmd  = ['admin', 'config', 'fetch']
        ydb_cli  = cli.YDB.from_module(module)
        rc, stdout, stderr = ydb_cli(ydb_cmd)
        if rc != 0:
            result['msg'] = f'command: "ydb admin config fetch" failed'
            result['stderr'] = stderr
            module.fail_json(**result)
        else:
            version = 0
            match = re.search(r'version:\s*(\d+)', stdout)
            if match:
                version = int(match.group(1))
            result['msg'] = ''
            result['version'] = version
            module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
