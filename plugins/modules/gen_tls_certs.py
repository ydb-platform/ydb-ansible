from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.gen_tls_certs_impl import gen_tls_certs

import io
import os
import tempfile


def write_file(atomic_move):
    def write_file_impl(path, content):
        # Create a temporary file
        dir_name = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(delete=False, dir=dir_name) as temp_file:
            temp_file.write(content.encode('utf-8'))
            temp_file.flush()
            temp_file_name = temp_file.name

        # Move the temporary file to the destination atomically
        atomic_move(temp_file_name, path)
    return write_file_impl

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
            fqdn=module.params.get('fqdn'),
            folder=module.params.get('folder'),
            dest=module.params.get('dest'),
            run_command=module.run_command,
            write_file=write_file(module.atomic_move),
            debug_info=string_stream
        )
        result['msg'] = string_stream.getvalue()
        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()
