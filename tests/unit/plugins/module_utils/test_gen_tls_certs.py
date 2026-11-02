import io
import os
import shutil
import sys
import tempfile
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
plugins_dir = os.path.join(current_dir, "../../../../plugins")
sys.path.insert(0, plugins_dir)

from module_utils.gen_tls_certs_impl import gen_tls_certs, write_file


def _run_command_without_openssl(command):
    """Record openssl outputs as dummy files so certificate layout can be tested."""
    parts = command.split()
    if parts[0] == "cp":
        src = parts[2]
        dest = parts[3]
        if dest.endswith("/"):
            dest = os.path.join(dest, os.path.basename(src))
        shutil.copy(src, dest)
        return
    if "-out" in parts:
        out = parts[parts.index("-out") + 1]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as handle:
            handle.write("dummy\n")
        return
    raise AssertionError("unexpected command: %s" % command)


class TestGenTlsCerts(unittest.TestCase):
    def test_certificate_directory_uses_exact_fqdn(self):
        folder = tempfile.mkdtemp(prefix="ydb-tls-")
        previous = os.getcwd()
        try:
            fqdn = "node1.zone-a.example.com"
            gen_tls_certs(
                fqdn=fqdn,
                folder=folder,
                dest="2026-11-02_00-00-00",
                run_command=_run_command_without_openssl,
                write_file=write_file,
                debug_info=io.StringIO(),
            )

            node_dir = os.path.join(folder, "certs", "2026-11-02_00-00-00", fqdn)
            short_dir = os.path.join(folder, "certs", "2026-11-02_00-00-00", "node1")
            self.assertTrue(os.path.isdir(node_dir))
            self.assertFalse(os.path.exists(short_dir))
            for filename in ("node.crt", "node.key", "web.pem", "options.cnf"):
                self.assertTrue(os.path.isfile(os.path.join(node_dir, filename)))

            with open(os.path.join(node_dir, "options.cnf")) as handle:
                config = handle.read()
            self.assertIn("DNS.1=%s\n" % fqdn, config)
            self.assertNotIn("DNS.1=node1\n", config)
        finally:
            os.chdir(previous)
            shutil.rmtree(folder)

    def test_same_short_name_in_two_zones_gets_separate_directories(self):
        folder = tempfile.mkdtemp(prefix="ydb-tls-")
        previous = os.getcwd()
        try:
            dest = "2026-11-02_00-00-00"
            fqdns = (
                "node1.zone-a.example.com",
                "node1.zone-b.example.com",
            )
            for fqdn in fqdns:
                gen_tls_certs(
                    fqdn=fqdn,
                    folder=folder,
                    dest=dest,
                    run_command=_run_command_without_openssl,
                    write_file=write_file,
                    debug_info=io.StringIO(),
                )

            for fqdn in fqdns:
                node_dir = os.path.join(folder, "certs", dest, fqdn)
                self.assertTrue(os.path.isfile(os.path.join(node_dir, "node.crt")))
                with open(os.path.join(node_dir, "options.cnf")) as handle:
                    self.assertIn("DNS.1=%s\n" % fqdn, handle.read())
            self.assertFalse(
                os.path.exists(os.path.join(folder, "certs", dest, "node1"))
            )
        finally:
            os.chdir(previous)
            shutil.rmtree(folder)


if __name__ == "__main__":
    unittest.main()
