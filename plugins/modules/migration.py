import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump

DOCUMENTATION = r'''
    name: migration
    plugin_type: module
    short_description: Manipulations with configs for migration
    description: |
        Migration from V1 to V2
        Migration from V2 to V1
'''

def compare_dict(dict1, dict2):
    if len(dict1) != len(dict2):
        return False

    for key, item in dict1.values():
        if key not in dict2:
            return False
        
        if not compare_item(item, dict2[key]):
            return False
    
    return True

def compare_list(list1, list2):
    if len(list1) != len(list2):
        return False

    for item1, item2 in zip(list1, list2):
        if not compare_item(item1, item2):
            return False

    return True

def compare_item(item1, item2):
    if isinstance(item1, list) and isinstance(item2, list):
        return compare_list(item1, item2)
    
    if isinstance(item1, dict) and isinstance(item2, dict):
        return compare_dict(item1, item2)
    
    return item1 == item2

def merge_static_dynamic(static_config, dynamic_config):
    """
    Merge static and dynamic config
    """
    output = dynamic_config

    for section in static_config:
        if section in output['config'] and not compare_item(output['config'][section],static_config[section]):
            print(f'PROBLEM: {section} is present in both configs and it\'s different, correct it manually')
            os._exit(1)
        else:
            output['config'][section] = static_config[section]
    if 'feature_flags' not in output['config']:
        output['config']['feature_flags'] = {}
    output['config']['feature_flags']['switch_to_config_v2'] = True
    return output

def cleanup(config):
    output = {}
    sections_to_skip = [
        'actor_system_config',
        'storage_config_generation',
        'blob_storage_config',
        'static_erasure']

    for section in config:
        if section in sections_to_skip:
            continue
        if section == 'config':
            output['config'] = {}
            for subsection in config['config']:
                match subsection:
                    case 'domains_config':
                        if 'domain' in config['config']['domains_config'] and 'name' in  config['config']['domains_config']['domain'][0]:
                            # output['config']['domains_config'] = {"domain": [{"name": config['config']['domains_config']['domain'][0]["name"]}]}
                            output['config']['domain_name'] = config['config']['domains_config']['domain'][0]["name"]
                        if 'security_config' in config['config']['domains_config']:
                            output['config']['security_config'] = config['config']['domains_config']['security_config']
                        else:
                            output['config']['security_config'] = {}
                        if 'disable_builtin_security' in config['config']['domains_config']:
                            output['config']['security_config']['disable_builtin_security'] = config['config']['domains_config']['disable_builtin_security']
                        if 'storage_pool_types' in config['config']['domains_config']['domain'][0]:
                            output['config']['storage_pool_types'] = config['config']['domains_config']['domain'][0]['storage_pool_types']
                            # config['config']['domains_config']['domain'][0]['storage_pool_types'] = {}
                            # del config['config']['domains_config']['domain'][0]['storage_pool_types']
                        if 'state_storage' in config['config']['domains_config']:
                            del config['config']['domains_config']['state_storage']
                        continue
                    case 'static_erasure':
                        section_newname = 'erasure'
                        fail_domain_type = 'rack'
                        if config['config'][subsection] == 'mirror-3-dc' and len(config['config']['hosts']) <= 6:
                            """
                            setup disk erasure level if not enough nodes (3-nodes-mirror-3dc or 6-nodes-bridge-2dc)
                            """
                            fail_domain_type = 'disk'
                        output['config']['fail_domain_type'] = fail_domain_type
                        output['config']['erasure'] = config['config'][subsection]
                        continue
                if subsection in sections_to_skip:
                    continue
                output['config'][subsection] = config['config'][subsection]
        else:
            # if section == 'metadata':
            #     if 'version' in config[section]:
            #         config[section]['version'] = config[section]['version'] + 1
            output[section] = config[section]

    return output

def empty_dynamic_config():
    """
    Generate empty dynamic config
    """
    return yaml.load("""---

metadata:
    kind: MainConfig
    cluster: ""
    version: 0
config:
    yaml_config_enabled: true
""", Loader=yaml.FullLoader)

def main():
    argument_spec = dict(
        static_config   = dict(type='raw', required=True),
        dynamic_config  = dict(type='raw', required=True),
        output_file     = dict(type='str', required=True),
        mode            = dict(type='str', required=False, default="v2"),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = {'changed': False}

    try:
        static_config = module.params.get('static_config')
        dynamic_config= module.params.get('dynamic_config')
        output_file   = module.params.get('output_file')
        mode          = module.params.get('mode','v2')

        result = {'changed': False}
        result_config = {}

        if mode == 'v2':
            if len(dynamic_config) == 0 or 'config' not in dynamic_config:
                dynamic_config = empty_dynamic_config()
            result_config = merge_static_dynamic(static_config, dynamic_config)
            result['changed'] = True
        elif mode == 'v2-self-management':
            result_config = dynamic_config
            result_config['config']['self_management_config'] = {'enabled': True}
            result['changed'] = True
        elif mode == 'v2-cleanup':
            result_config = cleanup(dynamic_config)
            result['changed'] = True

        if not module.check_mode:
            if output_file and result['changed']:
                try:
                    with open(output_file, 'w') as f:
                        safe_dump(result_config, f)
                except Exception as e:
                    module.fail_json(msg=f'Failed to write config: {str(e)}')
        else:
            result['msg'] = 'configuration would be saved (check mode)'

        module.exit_json(**result)
    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)

if __name__ == '__main__':
    main()
