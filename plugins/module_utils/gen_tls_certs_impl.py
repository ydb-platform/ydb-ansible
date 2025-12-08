#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys


def generate_ca_config(ca_cnf):
    ca_config_content = """[ ca ]
default_ca = CA_default

[ CA_default ]
default_days = 365
database = index.txt
serial = serial.txt
default_md = sha256
copy_extensions = copy
unique_subject = no

[ req ]
prompt=no
distinguished_name = distinguished_name
x509_extensions = extensions

[ distinguished_name ]
organizationName = YDB
commonName = YDB CA

[ extensions ]
keyUsage = critical,digitalSignature,nonRepudiation,keyEncipherment,keyCertSign
basicConstraints = critical,CA:true,pathlen:1

[ signing_policy ]
organizationName = supplied
commonName = optional

[ signing_node_req ]
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth,clientAuth

# Used to sign client certificates.
[ signing_client_req ]
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = clientAuth
"""
    write_file(ca_cnf, ca_config_content)


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def gen_tls_certs(fqdn, folder, dest, run_command, write_file, debug_info):
    key_bits = 4096
    secure_dir = os.path.join(folder, "secure")
    certs_dir = os.path.join(folder, "certs")
    nodes_dir = os.path.join(folder, "nodes")
    ca_cnf = os.path.join(folder, "ca.cnf")

    create_directory(folder)
    os.chdir(folder)

    create_directory(secure_dir)
    create_directory(certs_dir)
    create_directory(nodes_dir)

    if not os.path.isfile(ca_cnf):
        print("** Generating CA configuration file", file=debug_info)
        generate_ca_config(ca_cnf)

    if not os.path.isfile(os.path.join(secure_dir, "ca.key")):
        print("** Generating CA key", file=debug_info)
        run_command(
            f'openssl genrsa -out {os.path.join(secure_dir, "ca.key")} {key_bits}'
        )

    if not os.path.isfile(os.path.join(certs_dir, "ca.crt")):
        print("** Generating CA certificate", file=debug_info)
        run_command(
            f'openssl req -new -x509 -config {ca_cnf} -key {os.path.join(secure_dir, "ca.key")} -out {os.path.join(certs_dir, "ca.crt")} -days 1830 -batch'
        )

    if not os.path.isfile("index.txt"):
        open("index.txt", "a").close()

    if not os.path.isfile("serial.txt"):
        with open("serial.txt", "w") as f:
            f.write("01\n")

    def make_node_conf(safe_node, node, extra_nodes):
        node_dir = os.path.join(nodes_dir, safe_node)
        create_directory(node_dir)
        cfile = os.path.join(node_dir, "options.cnf")
        if not os.path.isfile(cfile):
            print(f"** Creating node configuration file for {node}...", file=debug_info)
            node_config_content = f"""# OpenSSL node configuration file
[ req ]
prompt=no
distinguished_name = distinguished_name
req_extensions = extensions

[ distinguished_name ]
organizationName = YDB

[ extensions ]
subjectAltName = @alt_names

[ alt_names ]
IP.1=127.0.1.1
DNS.1={node}
"""
            if extra_nodes:
                for i, nn in enumerate(extra_nodes.split(), start=2):
                    node_config_content += f"DNS.{i}={nn}\n"
            write_file(cfile, node_config_content)

    def make_node_key(safe_node, node):
        key_path = os.path.join(nodes_dir, safe_node, "node.key")
        if not os.path.isfile(key_path):
            print(f"** Generating key for node {node}...", file=debug_info)
            run_command(f"openssl genrsa -out {key_path} {key_bits}")

    def make_node_csr(safe_node, node):
        csr_path = os.path.join(nodes_dir, safe_node, "node.csr")
        if not os.path.isfile(csr_path):
            print(f"** Generating CSR for node {node}...", file=debug_info)
            run_command(
                f'openssl req -new -sha256 -config {os.path.join(nodes_dir, safe_node, "options.cnf")} -key {os.path.join(nodes_dir, safe_node, "node.key")} -out {csr_path} -batch'
            )

    def make_node_cert(safe_node, node):
        crt_path = os.path.join(nodes_dir, safe_node, "node.crt")
        if not os.path.isfile(crt_path):
            print(f"** Generating certificate for node {node}...", file=debug_info)
            run_command(
                f'openssl ca -config {ca_cnf} -keyfile {os.path.join(secure_dir, "ca.key")} -cert {os.path.join(certs_dir, "ca.crt")} -policy signing_policy -extensions signing_node_req -out {crt_path} -outdir {os.path.join(nodes_dir, safe_node)} -in {os.path.join(nodes_dir, safe_node, "node.csr")} -batch'
            )

        web_pem_path = os.path.join(nodes_dir, safe_node, "web.pem")
        if not os.path.isfile(web_pem_path):
            with open(web_pem_path, "w") as web_pem_file:
                with open(
                    os.path.join(nodes_dir, safe_node, "node.key")
                ) as key_file, open(crt_path) as crt_file, open(
                    os.path.join(certs_dir, "ca.crt")
                ) as ca_crt_file:
                    web_pem_file.write(key_file.read())
                    web_pem_file.write(crt_file.read())
                    web_pem_file.write(ca_crt_file.read())

    def move_node_files(safe_node):
        dest_dir = os.path.join(certs_dir, dest_name)
        create_directory(dest_dir)
        node_dir = os.path.join(nodes_dir, safe_node)
        dest_node_dir = os.path.join(dest_dir, safe_node)
        os.rename(node_dir, dest_node_dir)

    dest_name = dest
    dest_dir = os.path.join(certs_dir, dest_name)
    create_directory(dest_dir)
    run_command(f'cp -v {os.path.join(certs_dir, "ca.crt")} {dest_dir}/')

    node = fqdn.strip()
    short_node = node.split(".")[0]
    safe_node = short_node.replace("*", "_").replace("$", "_").replace("/", "_")
    make_node_conf(safe_node, short_node, node)
    make_node_key(safe_node, short_node)
    make_node_csr(safe_node, short_node)
    make_node_cert(safe_node, short_node)
    move_node_files(safe_node)

    print(f"All done. Certificates are in {dest_dir}", file=debug_info)

def run_command(command):
    subprocess.run(command, shell=True, check=True)

def write_file(path, content):
    with open(path, "w") as file:
        file.write(content)

def main():
    parser = argparse.ArgumentParser(description="Generate TLS certificates")

    parser.add_argument("--fqdn", metavar="fqdn", type=str, help="node FQDN")
    parser.add_argument(
        "--folder", metavar="folder", type=str, help="path to the working directory"
    )
    parser.add_argument(
        "--dest", metavar="dest", type=str, help="name of the destination directory"
    )

    args = parser.parse_args()
    gen_tls_certs(
        args.fqdn, args.folder, args.dest,
        run_command=run_command,
        write_file=write_file,
        debug_info=sys.stdout
    )

if __name__ == "__main__":
    main()
