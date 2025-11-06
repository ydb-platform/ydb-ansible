from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli

DOCUMENTATION = r'''
    name: workload
    plugin_type: module
    short_description: Run workload tests on YDB cluster
    description: |
        Run workload tests on YDB cluster
        `workload` possible values: topic, kv, stock
'''

def main():
    argument_spec=dict(
        workload=dict(type='str', default='stock'),
        enforce_user_token_requirement=dict(type='bool', default=False),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:

        password = module.params.get('password')
        user     = module.params.get('user')
        workload = module.params.get('workload')
        enforce_user_token_requirement = module.params.get('enforce_user_token_requirement')

        if user != '' and password != '' and enforce_user_token_requirement == True:
            ydb_cli  = cli.YDB.from_module(module, user=user, password=password)
        else:
            # Anonymouse mode
            ydb_cli  = cli.YDB.from_module(module)

        results = []

        if workload == 'topic':
            # https://ydb.tech/docs/ru/reference/ydb-cli/workload-topic
            ydb_cmd  = ['workload', 'topic', 'init', '--partitions', '16', '--consumers','2']
            rc, stdout, stderr = ydb_cli(ydb_cmd)
            if rc == 0:
                results.append(stdout)
                ydb_cmd  = ['workload', 'topic', 'run', 'write'] #, '--threads', '10', '--byte-rate 8M']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
                ydb_cmd  = ['workload', 'topic', 'run', 'full']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
            else:
                module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                result['msg'] = stderr
                module.fail_json(**result)
        elif workload == 'kv':
            # https://ydb.tech/docs/ru/reference/ydb-cli/workload-kv
            ydb_cmd  = ['workload', 'kv', 'init', '--init-upserts', '1000']
            rc, stdout, stderr = ydb_cli(ydb_cmd)
            if rc == 0:
                results.append(stdout)
                ydb_cmd  = ['workload', 'kv', 'run', 'upsert']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
                ydb_cmd  = ['workload', 'kv', 'run', 'insert']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
                ydb_cmd  = ['workload', 'kv', 'run', 'select']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
            else:
                module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                result['msg'] = stderr
                module.fail_json(**result)
        else:
            # https://ydb.tech/docs/ru/reference/ydb-cli/commands/workload/stock
            ydb_cmd  = ['workload', 'stock', 'init', '-p', '1000', '-q', '1000', '-o', '1000']
            rc, stdout, stderr = ydb_cli(ydb_cmd)
            if rc == 0:
                results.append(stdout)
                ydb_cmd  = ['workload', 'stock', 'run', 'user-hist']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
                ydb_cmd  = ['workload', 'stock', 'run', 'rand-user-hist']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
                ydb_cmd  = ['workload', 'stock', 'run', 'add-rand-order']
                rc, stdout, stderr = ydb_cli(ydb_cmd)
                results.append(stdout)
                if rc != 0:
                    module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                    result['msg'] = stderr
                    module.fail_json(**result)
            else:
                module.log(f'workload failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}')
                result['msg'] = stderr
                module.fail_json(**result)

        result['msg'] = "\n".join(results)
        module.exit_json(**result)
    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)

if __name__ == '__main__':
    main()

