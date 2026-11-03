#!/usr/bin/env python3
"""Validate one YDB node certificate set on the control node.

The checker uses the OpenSSL CLI and never prints key or certificate material.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone


KEY_LABELS = {"PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY"}
CERTIFICATE_LABEL = "CERTIFICATE"
PEM_RE = re.compile(
    r"-----BEGIN ([A-Z0-9 ]+)-----\n(.*?)\n-----END \1-----",
    re.S,
)
NOT_BEFORE_SKEW = timedelta(minutes=5)


class CertificateValidationError(Exception):
    """The certificate set cannot be installed safely."""


class PemBlock:
    def __init__(self, label, body):
        self.label = label
        self.text = "-----BEGIN %s-----\n%s\n-----END %s-----\n" % (label, body, label)


def fail(message):
    raise CertificateValidationError(message)


def clean(text):
    return " ".join((text or "").split())[:500]


def openssl(args, data=None):
    binary = shutil.which("openssl")
    if binary is None:
        fail("openssl is required on the control node")
    completed = subprocess.run(
        [binary, *args],
        input=None if data is None else data.encode("ascii"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed


def require_regular_file(path):
    if not os.path.isfile(path):
        fail("%s is missing" % path)
    if os.path.getsize(path) == 0:
        fail("%s is empty" % path)
    if not os.access(path, os.R_OK):
        fail("%s is not readable" % path)


def pem_blocks(path):
    try:
        with open(path, "r", encoding="utf-8") as pem_file:
            text = pem_file.read().replace("\r\n", "\n")
    except UnicodeError:
        fail("%s is not a PEM file" % path)
    blocks = [PemBlock(label, body.strip()) for label, body in PEM_RE.findall(text)]
    if not blocks:
        fail("%s does not contain a PEM object" % path)
    return blocks


def certificates(path):
    blocks = [block for block in pem_blocks(path) if block.label == CERTIFICATE_LABEL]
    if not blocks:
        fail("%s does not contain a certificate" % path)
    for block in blocks:
        result = openssl(["x509", "-noout"], block.text)
        if result.returncode != 0:
            fail("%s contains an unreadable certificate: %s" % (path, clean(result.stderr)))
    return blocks


def private_key(path):
    keys = []
    for block in pem_blocks(path):
        if "ENCRYPTED" in block.label:
            fail("%s must be an unencrypted private key" % path)
        if block.label in KEY_LABELS:
            keys.append(block)
    if not keys:
        fail("%s does not contain a private key" % path)
    return keys[0]


def public_key(private_or_certificate, certificate=False):
    args = ["x509", "-pubkey", "-noout"] if certificate else ["pkey", "-pubout"]
    result = openssl(args, private_or_certificate)
    if result.returncode != 0:
        kind = "certificate" if certificate else "private key"
        fail("cannot read the %s: %s" % (kind, clean(result.stderr)))
    lines = []
    for line in result.stdout.decode("ascii", "replace").splitlines():
        if line and not line.startswith("-----"):
            lines.append(line.strip())
    if not lines:
        fail("OpenSSL did not return a public key")
    return "".join(lines)


def fingerprint(certificate):
    result = openssl(["x509", "-noout", "-fingerprint", "-sha256"], certificate)
    if result.returncode != 0:
        fail("cannot fingerprint the certificate: %s" % clean(result.stderr))
    text = result.stdout.decode("ascii", "replace")
    match = re.search(r"Fingerprint=([0-9A-Fa-f:]+)", text)
    if match is None:
        fail("OpenSSL did not return a certificate fingerprint")
    return match.group(1).replace(":", "").lower()


def parse_openssl_date(value):
    normalized = value.strip().replace("  ", " ")
    if normalized.endswith(" GMT"):
        normalized = normalized[:-4]
    try:
        parsed = datetime.strptime(normalized, "%b %d %H:%M:%S %Y")
    except ValueError:
        fail("cannot parse certificate date %r" % value)
    return parsed.replace(tzinfo=timezone.utc)


def validity_dates(certificate):
    result = openssl(["x509", "-noout", "-dates"], certificate)
    if result.returncode != 0:
        fail("cannot read the certificate validity: %s" % clean(result.stderr))
    text = result.stdout.decode("ascii", "replace")
    not_before = re.search(r"notBefore=(.+)", text)
    not_after = re.search(r"notAfter=(.+)", text)
    if not_before is None or not_after is None:
        fail("the certificate does not contain validity dates")
    return parse_openssl_date(not_before.group(1)), parse_openssl_date(not_after.group(1))


def identity_names(certificate):
    names = set()
    extension = openssl(["x509", "-noout", "-ext", "subjectAltName"], certificate)
    if extension.returncode == 0:
        text = extension.stdout.decode("ascii", "replace")
        for value in re.findall(r"(?:DNS|IP Address|IP):([^,\n]+)", text):
            names.add(value.strip().rstrip(".").lower())
    subject = openssl(
        ["x509", "-noout", "-subject", "-nameopt", "RFC2253"],
        certificate,
    )
    if subject.returncode == 0:
        text = subject.stdout.decode("ascii", "replace").split("=", 1)[-1]
        for value in re.findall(r"(?:^|,)\s*CN=([^,]+)", text):
            names.add(value.strip().rstrip(".").lower())
    return names


def validate(ca_path, cert_path, key_path, web_path, names):
    for path in (ca_path, cert_path, key_path, web_path):
        require_regular_file(path)

    certificates(ca_path)
    leaf = certificates(cert_path)[0]
    node_public = public_key(leaf.text, certificate=True)
    if public_key(private_key(key_path).text) != node_public:
        fail("node.key does not match node.crt")

    not_before, not_after = validity_dates(leaf.text)
    now = datetime.now(timezone.utc)
    if not_before - NOT_BEFORE_SKEW > now:
        fail("node.crt is not valid yet")
    if not_after <= now:
        fail("node.crt is expired")

    required = {name.strip().rstrip(".").lower() for name in names if name and name.strip()}
    if not required:
        fail("at least one node name is required")
    found = identity_names(leaf.text)
    if required.isdisjoint(found):
        fail(
            "node.crt identifies %s, but the node name must be one of: %s"
            % (", ".join(sorted(found)) or "<no DNS, IP, or CN name>", ", ".join(sorted(required)))
        )

    verified = openssl(["verify", "-CAfile", ca_path, cert_path])
    if verified.returncode != 0 or b": OK" not in verified.stdout:
        detail = clean(verified.stdout.decode("utf-8", "replace") + " " + verified.stderr.decode("utf-8", "replace"))
        fail("node.crt was not issued by ca.crt%s" % (": " + detail if detail else ""))

    web_key = private_key(web_path)
    if public_key(web_key.text) != node_public:
        fail("the private key in web.pem does not match node.crt")
    leaf_fingerprint = fingerprint(leaf.text)
    web_fingerprints = [fingerprint(block.text) for block in certificates(web_path)]
    if leaf_fingerprint not in web_fingerprints:
        fail("web.pem does not contain node.crt")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Validate a YDB node certificate set.")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--web", required=True)
    parser.add_argument("--name", action="append", required=True, dest="names")
    parser.add_argument("--label", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        validate(args.ca, args.cert, args.key, args.web, args.names)
    except CertificateValidationError as exc:
        print(
            "TLS certificate validation failed for %s: %s" % (args.label, exc),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
