import re
import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def main():
    table_name = '`_ansible_test_table`'
    column_name = '`_ansible_column`'
    test_queries = [
        f'CREATE TABLE {table_name} ({column_name} Int64, PRIMARY KEY ({column_name}));',
        f'INSERT INTO {table_name} ({column_name}) VALUES (1), (2), (3);',
        f'''SELECT
                COUNT(*) AS count,
                Ensure(SUM({column_name}), SUM({column_name}) == 6, "wrong SUM") AS sum
            FROM {table_name};''',
        f'DROP TABLE {table_name};',
    ]
    argument_spec=dict(
        new_password=dict(type='str', default=None, no_log=True),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)

    result = {'changed': False}
    ydb_cli = cli.YDB.from_module(module)
    details = '—'
    try:
        for query in test_queries:
            rc, stdout, stderr = ydb_cli(['yql', '-s', query, '--format', 'json-unicode'])
            if rc != 0:
                result['msg'] = f'test query "{query}" failed with rc: {rc}, stdout: {stdout}, stderr: {stderr}'
                module.fail_json(**result)
                return
            elif query.startswith('SELECT'):
                details = stdout
        result['msg'] = f'all test queries were successful, details: {details}'
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
