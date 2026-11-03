"""Build small OpenSSL certificate trees for YDB certificate tests."""

import subprocess
from pathlib import Path


class NodeMaterial:
    def __init__(self, hostname, directory, key_path, certificate_path, web_path):
        self.hostname = hostname
        self.short_name = hostname.split(".", 1)[0]
        self.directory = directory
        self.key_path = key_path
        self.certificate_path = certificate_path
        self.web_path = web_path


def run_openssl(args):
    completed = subprocess.run(
        ["openssl", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
        raise RuntimeError("openssl %s failed\n%s" % (" ".join(args), detail))
    return completed


def make_ca(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    key = directory / ("%s.key" % name.replace(" ", "-"))
    cert = directory / ("%s.crt" % name.replace(" ", "-"))
    run_openssl([
        "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(key),
        "-out", str(cert),
        "-days", "30",
        "-nodes",
        "-subj", "/O=YDB/CN=%s" % name,
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    ])
    return key, cert


def make_key(path):
    run_openssl(["genrsa", "-out", str(path), "2048"])


def make_csr(key_path, csr_path):
    run_openssl([
        "req", "-new",
        "-key", str(key_path),
        "-out", str(csr_path),
        "-subj", "/O=YDB",
    ])


def sign_request(csr_path, ca_key, ca_cert, cert_path, dns_names, start=None, end=None):
    if start is None and end is None:
        extension = cert_path.with_suffix(".ext")
        extension.write_text("subjectAltName=%s\n" % ",".join("DNS:%s" % name for name in dns_names))
        run_openssl([
            "x509", "-req",
            "-in", str(csr_path),
            "-CA", str(ca_cert),
            "-CAkey", str(ca_key),
            "-CAcreateserial",
            "-out", str(cert_path),
            "-days", "30",
            "-extfile", str(extension),
        ])
        return

    work = cert_path.parent / "ca-work"
    new_certs = work / "newcerts"
    new_certs.mkdir(parents=True, exist_ok=True)
    (work / "index.txt").write_text("")
    (work / "index.txt.attr").write_text("unique_subject = no\n")
    (work / "serial").write_text("01\n")
    san = ",".join("DNS:%s" % name for name in dns_names)
    config = work / "ca.cnf"
    config.write_text(
        "\n".join([
            "[ ca ]",
            "default_ca = CA_default",
            "[ CA_default ]",
            "database = %s" % (work / "index.txt"),
            "serial = %s" % (work / "serial"),
            "new_certs_dir = %s" % new_certs,
            "policy = policy_any",
            "x509_extensions = node_ext",
            "default_md = sha256",
            "unique_subject = no",
            "copy_extensions = none",
            "[ policy_any ]",
            "organizationName = optional",
            "commonName = optional",
            "[ node_ext ]",
            "subjectAltName = %s" % san,
            "basicConstraints = CA:FALSE",
            "keyUsage = digitalSignature,keyEncipherment",
            "extendedKeyUsage = serverAuth,clientAuth",
            "",
        ])
    )
    run_openssl([
        "ca", "-config", str(config),
        "-cert", str(ca_cert),
        "-keyfile", str(ca_key),
        "-in", str(csr_path),
        "-out", str(cert_path),
        "-batch", "-notext",
        "-startdate", start,
        "-enddate", end,
    ])


def write_web(key_path, certificate_path, ca_paths, web_path):
    parts = [key_path.read_text(), certificate_path.read_text()]
    for ca_path in ca_paths:
        parts.append(ca_path.read_text())
    web_path.write_text("".join(parts))


def make_node(directory, hostname, ca_key, ca_cert, dns_names=None, start=None, end=None, ca_bundle=None):
    directory.mkdir(parents=True, exist_ok=True)
    key = directory / "node.key"
    csr = directory / "node.csr"
    cert = directory / "node.crt"
    web = directory / "web.pem"
    names = dns_names if dns_names is not None else [hostname.split(".", 1)[0], hostname]
    make_key(key)
    make_csr(key, csr)
    sign_request(csr, ca_key, ca_cert, cert, names, start=start, end=end)
    write_web(key, cert, ca_bundle or [ca_cert], web)
    return NodeMaterial(hostname, directory, key, cert, web)


def build_tls_tree(root, hostnames):
    ca_key, ca_cert = make_ca(root / "_ca", "YDB CA")
    (root / "ca.crt").write_text(ca_cert.read_text())
    nodes = {}
    for hostname in hostnames:
        short_name = hostname.split(".", 1)[0]
        nodes[hostname] = make_node(root / short_name, hostname, ca_key, ca_cert)
    return {"ca_key": ca_key, "ca_cert": ca_cert, "nodes": nodes}
