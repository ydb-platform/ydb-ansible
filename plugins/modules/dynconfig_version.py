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
    result = {'changed': False, 'version': 0}
    try:
        ydb_cmd  = ['admin', 'config', 'fetch']
        ydb_cli  = cli.YDB.from_module(module)
        rc, stdout, stderr = ydb_cli(ydb_cmd)
        if rc != 0:
            # We get 1 exit code if no YAML config in cluster
            result['msg'] = f'command: "ydb admin config fetch" failed'
        else:
            match = re.search(r'version:\s*(\d+)', stdout)
            if match:
                version = int(match.group(1))
                result['version'] = version
            result['msg'] = ''
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
