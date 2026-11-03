import os
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT))

from tls_fixture import build_tls_tree, make_key


HOSTS = ("node1.example.net", "node2.example.net")


def private_lines(path):
    text = path.read_text()
    lines = []
    blocks = re.findall(
        r"-----BEGIN ([A-Z0-9 ]+)-----\n(.*?)\n-----END \1-----",
        text,
        re.S,
    )
    for label, body in blocks:
        if "PRIVATE" not in label:
            continue
        lines.append("-----BEGIN %s-----" % label)
        lines.extend(line for line in body.splitlines() if line.strip())
    return lines


def changed_count(output):
    recap = output.split("PLAY RECAP", 1)[1]
    return sum(int(value) for value in re.findall(r"changed=(\d+)", recap))


class UpdateCertsPlaybookTest(unittest.TestCase):
    def setUp(self):
        if subprocess.run(
            ["sudo", "-n", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode != 0:
            self.skipTest("passwordless sudo is required")
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ydb-certs-"))
        self.addCleanup(lambda: subprocess.run(["sudo", "rm", "-rf", str(self.tmpdir)], check=True))
        collection_root = self.tmpdir / "collections"
        collection = collection_root / "ansible_collections" / "ydb_platform"
        collection.mkdir(parents=True)
        (collection / "ydb").symlink_to(ROOT)
        config = self.tmpdir / "ansible.cfg"
        config.write_text(
            "\n".join([
                "[defaults]",
                "collections_path = %s" % collection_root,
                "host_key_checking = False",
                "retry_files_enabled = False",
                "stdout_callback = default",
                "deprecation_warnings = False",
                "forks = 5",
                "",
            ])
        )
        self.env = os.environ.copy()
        self.env["ANSIBLE_CONFIG"] = str(config)
        self.env["ANSIBLE_COLLECTIONS_PATH"] = str(collection_root)
        self.env["ANSIBLE_FORCE_COLOR"] = "0"
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"

    def write_inventory(self, tls_dir, node_dirs, host_user="ydb"):
        inventory = self.tmpdir / "inventory.yaml"
        host_lines = []
        for hostname, node_dir in node_dirs.items():
            host_lines.append("    %s:" % hostname)
            host_lines.append("      ydb_dir: %s" % node_dir)
        inventory.write_text(
            "\n".join([
                "all:",
                "  vars:",
                "    ansible_connection: local",
                "    ansible_python_interpreter: /usr/bin/python3",
                "    ydb_host_user: %s" % host_user,
                "    ydb_tls_dir: %s" % tls_dir,
                "ydb:",
                "  hosts:",
                *host_lines,
                "",
            ])
        )
        return inventory

    def run_playbook(self, inventory):
        completed = subprocess.run(
            [
                "ansible-playbook",
                str(ROOT / "playbooks" / "update_certs.yaml"),
                "-i", str(inventory),
                "--diff",
            ],
            cwd=str(ROOT),
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
        )
        return completed

    def prepare_nodes(self, tls_root):
        node_dirs = {}
        for hostname in HOSTS:
            node_dir = self.tmpdir / hostname
            node_dir.mkdir()
            node_dirs[hostname] = node_dir
        return node_dirs, build_tls_tree(tls_root, HOSTS)

    def write_sentinel(self, node_dir):
        certs = node_dir / "certs"
        certs.mkdir()
        sentinel = certs / "ca.crt"
        sentinel.write_text("old-ca\n")
        return sentinel

    def test_install_is_idempotent_and_hides_private_keys(self):
        tls_root = self.tmpdir / "tls"
        node_dirs, material = self.prepare_nodes(tls_root)
        inventory = self.write_inventory(tls_root, node_dirs)
        secrets = []
        for node in material["nodes"].values():
            secrets.extend(private_lines(node.key_path))
            secrets.extend(private_lines(node.web_path))

        first = self.run_playbook(inventory)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertGreater(changed_count(first.stdout), 0)
        for line in secrets:
            self.assertNotIn(line, first.stdout)

        for hostname, node_dir in node_dirs.items():
            node = material["nodes"][hostname]
            certs = node_dir / "certs"
            ownership = subprocess.check_output(
                ["sudo", "stat", "-c", "%U %G %a", str(certs)],
                text=True,
            ).split()
            self.assertEqual(ownership, ["root", "certs", "750"])
            for name, source in (
                ("ca.crt", tls_root / "ca.crt"),
                ("node.crt", node.certificate_path),
                ("node.key", node.key_path),
                ("web.pem", node.web_path),
            ):
                installed = certs / name
                file_ownership = subprocess.check_output(
                    ["sudo", "stat", "-c", "%U %G %a", str(installed)],
                    text=True,
                ).split()
                self.assertEqual(file_ownership, ["root", "certs", "440"])
                installed_hash = subprocess.check_output(
                    ["sudo", "sha256sum", str(installed)],
                    text=True,
                ).split()[0]
                source_hash = subprocess.check_output(
                    ["sha256sum", str(source)],
                    text=True,
                ).split()[0]
                self.assertEqual(installed_hash, source_hash)
            stage = subprocess.run(
                ["sudo", "test", "!", "-e", str(node_dir / ".ydbd-cert-staging")],
                check=False,
            )
            self.assertEqual(stage.returncode, 0)

        second = self.run_playbook(inventory)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(changed_count(second.stdout), 0)
        for line in secrets:
            self.assertNotIn(line, second.stdout)

    def test_replaces_an_existing_certificate_set(self):
        tls_root = self.tmpdir / "tls"
        node_dirs, _old_material = self.prepare_nodes(tls_root)
        inventory = self.write_inventory(tls_root, node_dirs)
        first = self.run_playbook(inventory)
        self.assertEqual(first.returncode, 0, first.stdout)

        replacement_root = self.tmpdir / "replacement"
        replacement = build_tls_tree(replacement_root, HOSTS)
        inventory = self.write_inventory(replacement_root, node_dirs)
        updated = self.run_playbook(inventory)
        self.assertEqual(updated.returncode, 0, updated.stdout)
        self.assertGreater(changed_count(updated.stdout), 0)
        for hostname, node_dir in node_dirs.items():
            node = replacement["nodes"][hostname]
            for name, source in (
                ("ca.crt", replacement_root / "ca.crt"),
                ("node.crt", node.certificate_path),
                ("node.key", node.key_path),
                ("web.pem", node.web_path),
            ):
                installed_hash = subprocess.check_output(
                    ["sudo", "sha256sum", str(node_dir / "certs" / name)],
                    text=True,
                ).split()[0]
                source_hash = subprocess.check_output(["sha256sum", str(source)], text=True).split()[0]
                self.assertEqual(installed_hash, source_hash)
        secrets = []
        for node in replacement["nodes"].values():
            secrets.extend(private_lines(node.key_path))
            secrets.extend(private_lines(node.web_path))
        for line in secrets:
            self.assertNotIn(line, updated.stdout)

        repeated = self.run_playbook(inventory)
        self.assertEqual(repeated.returncode, 0, repeated.stdout)
        self.assertEqual(changed_count(repeated.stdout), 0)

    def test_existing_service_account_joins_certificate_group(self):
        account = "ydbct" + uuid.uuid4().hex[:8]
        subprocess.run(
            ["sudo", "useradd", "--system", "--no-create-home", "--shell", "/usr/sbin/nologin", account],
            check=True,
        )
        self.addCleanup(lambda: subprocess.run(["sudo", "userdel", account], check=False))
        tls_root = self.tmpdir / "tls"
        node_dirs, _material = self.prepare_nodes(tls_root)
        inventory = self.write_inventory(tls_root, node_dirs, host_user=account)

        first = self.run_playbook(inventory)
        self.assertEqual(first.returncode, 0, first.stdout)
        groups = subprocess.check_output(["id", "-nG", account], text=True).split()
        self.assertIn("certs", groups)

        second = self.run_playbook(inventory)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(changed_count(second.stdout), 0)

    def test_missing_source_does_not_change_any_node(self):
        tls_root = self.tmpdir / "tls"
        node_dirs, material = self.prepare_nodes(tls_root)
        material["nodes"]["node2.example.net"].key_path.unlink()
        sentinels = {hostname: self.write_sentinel(node_dir) for hostname, node_dir in node_dirs.items()}
        inventory = self.write_inventory(tls_root, node_dirs)

        completed = self.run_playbook(inventory)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("missing", completed.stdout)
        for sentinel in sentinels.values():
            self.assertEqual(sentinel.read_text(), "old-ca\n")
            self.assertFalse((sentinel.parent / "node.key").exists())

    def test_mismatched_key_does_not_change_any_node(self):
        tls_root = self.tmpdir / "tls"
        node_dirs, material = self.prepare_nodes(tls_root)
        make_key(material["nodes"]["node1.example.net"].key_path)
        sentinels = {hostname: self.write_sentinel(node_dir) for hostname, node_dir in node_dirs.items()}
        inventory = self.write_inventory(tls_root, node_dirs)

        completed = self.run_playbook(inventory)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("does not match", completed.stdout)
        for sentinel in sentinels.values():
            self.assertEqual(sentinel.read_text(), "old-ca\n")
            self.assertFalse((sentinel.parent / "node.crt").exists())


if __name__ == "__main__":
    unittest.main()
