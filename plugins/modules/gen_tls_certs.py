from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.gen_tls_certs_impl import gen_tls_certs

import io


def main():
    argument_spec=dict(
        fqdn=dict(type='str', required=True),
        folder=dict(type='str', required=True),
        dest=dict(type='str', required=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    try:
        string_stream = io.StringIO()
        result = {'changed': False}
        gen_tls_certs(
            module.params.get('fqdn'),
            module.params.get('folder'),
            module.params.get('dest'),
            string_stream
        )
        result['msg'] = string_stream.getvalue()
        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
