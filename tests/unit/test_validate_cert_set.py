import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT))

from tls_fixture import build_tls_tree, make_ca, make_key, make_node, write_web


SPEC = importlib.util.spec_from_file_location(
    "validate_cert_set",
    ROOT / "roles" / "ydbd_certs" / "files" / "validate_cert_set.py",
)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


HOST = "node1.example.net"


def names_for(hostname):
    return [hostname, hostname.split(".", 1)[0]]


class ValidateCertSetTest(unittest.TestCase):
    def test_valid_set_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            material = build_tls_tree(root, [HOST])
            node = material["nodes"][HOST]
            validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))

    def test_short_name_or_full_name_is_sufficient(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ca_key, ca_cert = make_ca(root / "_ca", "YDB CA")
            (root / "ca.crt").write_text(ca_cert.read_text())
            short_only = make_node(
                root / "short", HOST, ca_key, ca_cert, dns_names=[HOST.split(".", 1)[0]],
            )
            validator.validate(root / "ca.crt", short_only.certificate_path, short_only.key_path, short_only.web_path, names_for(HOST))
            full_only = make_node(root / "full", HOST, ca_key, ca_cert, dns_names=[HOST])
            validator.validate(root / "ca.crt", full_only.certificate_path, full_only.key_path, full_only.web_path, names_for(HOST))

    def test_missing_file_fails_before_reporting_key_material(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            material = build_tls_tree(root, [HOST])
            node = material["nodes"][HOST]
            key_text = node.key_path.read_text()
            node.key_path.unlink()
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("missing", str(raised.exception))
            self.assertNotIn("PRIVATE", str(raised.exception))
            self.assertNotIn(key_text.splitlines()[1], str(raised.exception))

    def test_mismatched_node_key_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            material = build_tls_tree(root, [HOST])
            node = material["nodes"][HOST]
            make_key(node.key_path)
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("node.key does not match", str(raised.exception))

    def test_web_pem_key_must_match_certificate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            material = build_tls_tree(root, [HOST])
            node = material["nodes"][HOST]
            other_key = root / "other.key"
            make_key(other_key)
            write_web(other_key, node.certificate_path, [material["ca_cert"]], node.web_path)
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("web.pem", str(raised.exception))

    def test_expired_certificate_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ca_key, ca_cert = make_ca(root / "_ca", "YDB CA")
            (root / "ca.crt").write_text(ca_cert.read_text())
            node = make_node(
                root / "node1", HOST, ca_key, ca_cert,
                start="200101000000Z", end="200102000000Z",
            )
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("expired", str(raised.exception))

    def test_not_yet_valid_certificate_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ca_key, ca_cert = make_ca(root / "_ca", "YDB CA")
            (root / "ca.crt").write_text(ca_cert.read_text())
            node = make_node(
                root / "node1", HOST, ca_key, ca_cert,
                start="301201000000Z", end="301231235959Z",
            )
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("not valid yet", str(raised.exception))

    def test_wrong_identity_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ca_key, ca_cert = make_ca(root / "_ca", "YDB CA")
            (root / "ca.crt").write_text(ca_cert.read_text())
            node = make_node(
                root / "node1", HOST, ca_key, ca_cert, dns_names=["other.example.net"],
            )
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("other.example.net", str(raised.exception))

    def test_ca_bundle_containing_the_issuing_ca_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_key, old_cert = make_ca(root / "old", "Old CA")
            new_key, new_cert = make_ca(root / "new", "New CA")
            (root / "ca.crt").write_text(old_cert.read_text() + new_cert.read_text())
            node = make_node(root / "node1", HOST, new_key, new_cert, ca_bundle=[old_cert, new_cert])
            validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))

    def test_unrelated_ca_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trusted_key, trusted_cert = make_ca(root / "trusted", "Trusted CA")
            other_key, other_cert = make_ca(root / "other", "Other CA")
            (root / "ca.crt").write_text(trusted_cert.read_text())
            node = make_node(root / "node1", HOST, other_key, other_cert)
            with self.assertRaises(validator.CertificateValidationError) as raised:
                validator.validate(root / "ca.crt", node.certificate_path, node.key_path, node.web_path, names_for(HOST))
            self.assertIn("was not issued", str(raised.exception))
            self.assertIsNotNone(trusted_key)

    def test_cli_failure_does_not_print_private_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            material = build_tls_tree(root, [HOST])
            node = material["nodes"][HOST]
            secret_lines = [line for line in node.key_path.read_text().splitlines() if line and not line.startswith("-----")]
            make_key(node.key_path)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = validator.main([
                    "--ca", str(root / "ca.crt"),
                    "--cert", str(node.certificate_path),
                    "--key", str(node.key_path),
                    "--web", str(node.web_path),
                    "--name", HOST,
                    "--label", HOST,
                ])
            self.assertEqual(code, 1)
            output = stderr.getvalue()
            self.assertIn("does not match", output)
            for line in secret_lines:
                self.assertNotIn(line, output)

    def test_playbook_has_no_preflight_dependency(self):
        playbook = (ROOT / "playbooks" / "update_certs.yaml").read_text()
        self.assertNotIn("preflight", playbook)
        metadata = (ROOT / "roles" / "ydbd_certs" / "meta" / "main.yaml").read_text()
        self.assertIn("allow_duplicates: false", metadata)
        installer = (ROOT / "roles" / "ydbd" / "tasks" / "main.yaml").read_text()
        self.assertIn("path={{ ydb_dir }}/certs group=certs owner=root mode='0750'", installer)


if __name__ == "__main__":
    unittest.main()
