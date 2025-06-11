from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils import cli


INVALID_PASSWORD = 'Invalid password'
SSL_HANDSHAKE_ERRORS = [
    'SSL_ERROR_SSL',
    'ssl3_get_record:wrong version number',
    'Ssl handshake failed',
    'failed to connect to all addresses'
]


def main():
    argument_spec=dict(
        fallback_to_default_user=dict(type='bool', default=True),
        wait_for_server=dict(type='bool', default=True),
        retry_on_ssl_error=dict(type='bool', default=True),
    )
    cli.YDB.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}
    try:
        ydb_cli = cli.YDB.from_module(module)
        rc, stdout, stderr = ydb_cli(['auth', 'get-token', '-f'])

        # Check for SSL handshake errors
        if rc != 0 and any(error in stderr for error in SSL_HANDSHAKE_ERRORS):
            if module.params.get('retry_on_ssl_error'):
                # Return a result that will trigger Ansible retry mechanism
                result['msg'] = (
                    'SSL/TLS handshake failed, but retries are enabled. '
                    'This could be due to YDB server not being fully started yet.'
                )
                result['stderr'] = stderr
                result['ssl_retry_needed'] = True
                result['debug_info'] = {
                    'ssl_error_detected': True,
                    'retry_enabled': True,
                    'endpoint': module.params.get('endpoint'),
                    'ca_file': module.params.get('ca_file'),
                    'common_solutions': [
                        'Wait longer for server startup',
                        'Check certificate configuration',
                        'Verify hostname resolution',
                        'Check YDB server logs',
                        'Verify certificate SAN includes all hostnames and IPs'
                    ]
                }
                # Exit with success but without token to trigger retry
                module.exit_json(**result)
            else:
                # Original behavior when retries are disabled
                result['msg'] = (
                    'SSL/TLS handshake failed. This could be due to: '
                    '1) YDB server not fully started (try waiting longer), '
                    '2) Certificate/hostname mismatch, '
                    '3) Server not ready to accept TLS connections, '
                    '4) TLS version incompatibility'
                )
                result['stderr'] = stderr
                result['debug_info'] = {
                    'ssl_error_detected': True,
                    'endpoint': module.params.get('endpoint'),
                    'ca_file': module.params.get('ca_file'),
                    'common_solutions': [
                        'Wait longer for server startup',
                        'Check certificate configuration',
                        'Verify hostname resolution',
                        'Check YDB server logs',
                        'Verify certificate SAN includes all hostnames and IPs'
                    ]
                }
                module.fail_json(**result)

        if rc != 0 and INVALID_PASSWORD in stderr and module.params.get('fallback_to_default_user'):
            module.log('falling back to default user')
            ydb_cli = cli.YDB.from_module(module, user='root', password='')
            rc, stdout, stderr = ydb_cli(['auth', 'get-token', '-f'])

        if rc != 0:
            result['msg'] = f'command: "ydb auth get-token" failed'
            result['stderr'] = stderr
            result['stdout'] = stdout
            module.fail_json(**result)

        module.no_log_values.add('token')
        token = stdout.strip()
        result['msg'] = 'command: "ydb auth get-token" succeeded'
        result['token'] = token
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
