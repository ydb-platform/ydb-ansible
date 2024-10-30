import os
import yaml

# Simple convertor for pre-collections configs for main branch config
# How to use:
# - Put this script into ansible folder with configs for pre-collections branch
# - Execute script (python3 pre-collections-convert.py)
# - Use generated 50-inventory.yml as an inventory file for main branch of YDB ansible collection
#
# How it works:
# - Get all records from files: hosts, group_vars/all, files/config.yaml
# - Get and agregate all information from these files as needed
# - Store result as YAML file

def read_yaml_file(file_path):
    try:
        with open(file_path, 'r') as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {exc}")
        return None

def read_hosts(file_path):
    try:
        hosts_data = {}
        with open(file_path, 'r') as stream:
            for line in stream.readlines():
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1]
                    hosts_data[section_name] = []
                else:
                    host_config = line.replace('\t',' ').split(' ')
                    if len(host_config) > 0:
                        host = {}
                        if len(host_config[0]) > 1:
                            host['host'] = host_config[0];
                            for i in range(1,len(host_config)):
                                if '=' in host_config[i]:
                                    host_attr = host_config[i].split('=')
                                    host[host_attr[0]] = host_attr[1]
                                # **dict(zip([f'ansible_{x}' for x in range(2, len(host_config))], host_config[2:]))
                            hosts_data[list(hosts_data.keys())[-1]].append(host)
        return hosts_data
    except Exception as e:
        print(f"Error reading hosts file: {e}")
        return {}

def generate_inventory(hosts,vars,yaml_config):
    h = {}
    for host_type in hosts:
        for host in hosts[host_type]:
            if host['host'] not in h:
                h[host['host']] = ''
    vars['ydb_allow_format_drives'] = False
    vars['ydb_skip_data_loss_confirmation_prompt'] = False
    return {'all':{'children':{'ydb':{'hosts':h, 'vars': vars}}}}

def main():
    file_path = 'hosts'
    hosts = read_hosts(file_path)

    file_path = 'group_vars/all'
    vars = read_yaml_file(file_path)
    if vars is None:
        print("Error: Unable to read YAML file {0}".format(file_path))
        return

    file_path = 'files/config.yaml'
    yaml_config = read_yaml_file(file_path)
    if yaml_config is None:
        print("Error: Unable to read YAML file {0}".format(file_path))
        return
    
    # Generate new configs for main branch
    file_path = "50-inventory.yml"
    print("Generating new inventory file\nOutput filename is {}".format(file_path))
    inv = generate_inventory(hosts,vars,yaml_config)
    print(inv)
    with open(file_path, 'w') as f:
        y = yaml.safe_dump(inv, default_flow_style=False).replace(r"''", '')
        f.write(y)

if __name__ == "__main__":
    main()