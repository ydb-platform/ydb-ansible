import json
import re
import yaml
import uuid


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils  import cli


def set_pdisk_active_status(ydb_dstool):
    """Set PDisk status to ACTIVE for any inactive PDisks"""
    rc, stdout, stderr = ydb_dstool(['pdisk', 'list', '--format=json'])
    if rc == 0:
        try:
            dstool_result = json.loads(stdout)
            for pdisk in dstool_result:
                if "Status" in pdisk and pdisk["Status"] != "ACTIVE":
                    ydb_dstool(['pdisk', 'set', '--status=ACTIVE', '--pdisk-ids', pdisk["NodeId:PDiskId"]])
        except Exception:
            # Ignore errors in PDisk status setting as it's not critical
            pass

def main():
    argument_spec=dict(
    )
    cli.DsTool.add_arguments(argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)
    result = {'changed': False}

    try:
        ydb_dstool = cli.DsTool.from_module(module)

        # Set PDisk status to ACTIVE if needed
        set_pdisk_active_status(ydb_dstool)

        result['changed'] = True
        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()