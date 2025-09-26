import yaml
import os
import copy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ydb_platform.ydb.plugins.module_utils.yaml_utils import safe_dump

def _ensure_config_path(config, path, default_value):
    """Helper function to ensure a nested config path exists with a default value."""
    current = config
    keys = path.split('.')

    # Navigate to the parent of the final key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final key if it doesn't exist
    final_key = keys[-1]
    if final_key not in current:
        current[final_key] = default_value

def _generate_hosts_section(hostvars, ydb_disks, default_disk_type=None):
    """Generate hosts section from inventory data when it's missing from config."""
    hosts = []

    # Get the list of YDB hosts from the inventory
    # We assume that hostvars contains only the relevant YDB hosts
    for hostname, host_data in hostvars.items():
        host_entry = {'host': hostname}

        # Generate drive section from ydb_disks
        if ydb_disks:
            drives = []
            for disk in ydb_disks:
                # Use the disk type from the disk definition, or fall back to default
                disk_type = disk.get('type')
                if not disk_type:
                    disk_type = default_disk_type or 'SSD'

                drive = {
                    'path': f"/dev/disk/by-partlabel/{disk.get('label', disk.get('name', '').replace('/dev/', ''))}",
                    'type': disk_type
                }
                drives.append(drive)
            host_entry['drive'] = drives

        # Add location information if available in host_data
        # Handle case where host_data might be None or not a dict
        if isinstance(host_data, dict):
            location_data = host_data.get('location', {})
            if location_data and isinstance(location_data, dict):
                location = {}
                if 'body' in location_data:
                    location['body'] = location_data['body']
                if 'data_center' in location_data:
                    location['data_center'] = location_data['data_center']
                # For 2DC scheme
                if 'pile' in location_data:
                    location['bridge_pile_name'] = location_data['pile']
                if 'rack' in location_data:
                    location['rack'] = location_data['rack']
                if location:
                    host_entry['location'] = location

        hosts.append(host_entry)

    return hosts

def patch_config_v2(config, hostvars=None, ydb_disks=None, groups=None, ydb_dir=None, ydb_domain=None):
    _ensure_config_path(config, 'yaml_config_enabled', True)
    _ensure_config_path(config, 'self_management_config.enabled', True)
    _ensure_config_path(config, 'actor_system_config.use_auto_config', True)

    # Add TLS configuration fields
    if ydb_dir is not None:
        _ensure_config_path(config, 'tls.cert', f"{ydb_dir}/certs/node.crt")
        _ensure_config_path(config, 'tls.key', f"{ydb_dir}/certs/node.key")
        _ensure_config_path(config, 'tls.ca', f"{ydb_dir}/certs/ca.crt")
        _ensure_config_path(config, 'grpc_config.cert', f"{ydb_dir}/certs/node.crt")
        _ensure_config_path(config, 'grpc_config.key', f"{ydb_dir}/certs/node.key")
        _ensure_config_path(config, 'grpc_config.ca', f"{ydb_dir}/certs/ca.crt")
        _ensure_config_path(config, 'grpc_config.services_enabled', ['legacy','discovery'])
    
    if ydb_domain is not None:
        _ensure_config_path(config, 'domains_config.domain', [{"name": f"{ydb_domain}"}])

    # Generate hosts section if it's missing and we have the required data
    if 'hosts' not in config and hostvars and ydb_disks:
        # Filter hostvars to only include YDB group hosts if groups is provided
        if groups and 'ydb' in groups:
            filtered_hostvars = {host: hostvars.get(host, {}) for host in groups['ydb'] if host in hostvars}
        else:
            # Fallback: use all hostvars if no groups filtering is available
            filtered_hostvars = hostvars

        default_disk_type = config.get('default_disk_type', 'SSD')
        config['hosts'] = _generate_hosts_section(filtered_hostvars, ydb_disks, default_disk_type)

    return config

def main():
    argument_spec = dict(
        config=dict(type='raw', required=True),
        output_file=dict(type='str', required=False),
        hostvars=dict(type='dict', required=False),
        ydb_disks=dict(type='list', required=False),
        groups=dict(type='dict', required=False),
        ydb_dir=dict(type='str', required=False, default=None),
        ydb_domain=dict(type='str', required=False, default=None),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = {'changed': False}

    try:
        config_input = module.params.get('config')
        output_file = module.params.get('output_file')
        hostvars = module.params.get('hostvars')
        ydb_disks = module.params.get('ydb_disks')
        groups = module.params.get('groups')
        ydb_dir = module.params.get('ydb_dir')
        ydb_domain = module.params.get('ydb_domain')

        # Handle different input types
        if isinstance(config_input, dict):
            # Config is already a dictionary
            config = config_input
        elif isinstance(config_input, str):
            # Config is a file path or YAML string
            if os.path.exists(config_input):
                # It's a file path
                with open(config_input, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                # It's a YAML string
                config = yaml.safe_load(config_input)
        else:
            result['msg'] = 'config must be a dictionary, file path, or YAML string'
            module.fail_json(**result)


        # Apply the patch to the config section only
        original_config = copy.deepcopy(config)
        if 'config' in config:
            patched_config_section = patch_config_v2(config['config'], hostvars, ydb_disks, groups, ydb_dir, ydb_domain)
            config['config'] = patched_config_section
        else:
            config = patch_config_v2(config, hostvars, ydb_disks, groups, ydb_dir, ydb_domain)

        # Determine if changes were actually made
        result['changed'] = config != original_config
        result['config'] = config

        # Write to output file if specified
        if output_file and not module.check_mode:
            with open(output_file, 'w') as f:
                safe_dump({'config': config}, f)
            result['msg'] = f'patched configuration written to {output_file}'
        else:
            result['msg'] = 'configuration patched successfully'

        module.exit_json(**result)

    except Exception as e:
        result['msg'] = f'unexpected exception: {e}'
        module.fail_json(**result)


if __name__ == '__main__':
    main()