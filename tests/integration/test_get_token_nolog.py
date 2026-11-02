import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "ydb-password-" + uuid.uuid4().hex
TOKEN = "ydb-token-" + uuid.uuid4().hex


class GetTokenNoLogTest(unittest.TestCase):
    def test_token_is_hidden_but_remains_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixtures(root)
            for verbosity in ([], ["-vvv"]):
                with self.subTest(verbosity=verbosity):
                    call_log = root / "calls.log"
                    call_log.write_text("")
                    result_file = root / "result.txt"
                    if result_file.exists():
                        result_file.unlink()
                    completed = self._run_playbook(root, verbosity)
                    output = completed.stdout + completed.stderr
                    self.assertEqual(
                        completed.returncode,
                        0,
                        output,
                    )
                    self.assertNotIn(TOKEN, output)
                    self.assertNotIn(PASSWORD, output)
                    self.assertIn("no_log", output)
                    self.assertEqual(result_file.read_text().strip(), "ok")
                    self.assertEqual(call_log.read_text().count("called"), 1)
                    if verbosity:
                        self.assertIn("censored", output)
                        self.assertNotIn("get-********", output)

    def _write_fixtures(self, root):
        token_file = root / "token.txt"
        token_file.write_text(TOKEN)
        call_log = root / "calls.log"

        ydb_bin = root / "ydb"
        ydb_bin.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env python3
            import os
            import pathlib
            import sys

            pathlib.Path(os.environ["CALL_LOG"]).open("a").write("called\\n")
            if "auth" in sys.argv and "get-token" in sys.argv:
                sys.stdout.write(pathlib.Path(os.environ["TOKEN_FILE"]).read_text())
                sys.exit(0)
            sys.stderr.write("unexpected args: %r\\n" % (sys.argv,))
            sys.exit(2)
        """))
        ydb_bin.chmod(ydb_bin.stat().st_mode | stat.S_IEXEC)

        collections = root / "cols"
        collection = collections / "ansible_collections" / "ydb_platform"
        collection.mkdir(parents=True)
        (collection / "ydb").symlink_to(PROJECT_ROOT)

        (root / "ansible.cfg").write_text(textwrap.dedent("""\
            [defaults]
            host_key_checking = False
            retry_files_enabled = False
            deprecation_warnings = False
            stdout_callback = default
        """))
        (root / "inventory").write_text(
            "localhost ansible_connection=local ansible_python_interpreter=%s\n" % sys_executable()
        )
        (root / "playbook.yaml").write_text(textwrap.dedent("""\
            ---
            - name: get_token must not print the access token
              hosts: localhost
              gather_facts: false
              tasks:
                - name: refuse to mint a token without no_log
                  ydb_platform.ydb.get_token:
                    ydb_bin: "{{ ydb_bin }}"
                    endpoint: grpcs://127.0.0.1:2135
                    database: /Root
                    user: root
                    password: "{{ ydb_password }}"
                    fallback_to_default_user: false
                    retry_on_ssl_error: false
                  register: refused
                  ignore_errors: true

                - name: refusal explains no_log and does not return a token
                  ansible.builtin.assert:
                    that:
                      - refused is failed
                      - "'token' not in refused"
                      - "'no_log' in refused.msg"

                - name: get token with no_log
                  ydb_platform.ydb.get_token:
                    ydb_bin: "{{ ydb_bin }}"
                    endpoint: grpcs://127.0.0.1:2135
                    database: /Root
                    user: root
                    password: "{{ ydb_password }}"
                    fallback_to_default_user: false
                    retry_on_ssl_error: false
                  register: ydb_credentials
                  until: "'token' in ydb_credentials"
                  retries: 1
                  delay: 1
                  no_log: true

                - name: record whether the registered token matches
                  ansible.builtin.copy:
                    dest: "{{ result_file }}"
                    content: "{{ 'ok' if (ydb_credentials.token | trim) == (lookup('file', token_file) | trim) else 'mismatch' }}"
                    mode: "0600"
                  no_log: true
        """))

    def _run_playbook(self, root, extra_args):
        env = os.environ.copy()
        env.update({
            "ANSIBLE_CONFIG": str(root / "ansible.cfg"),
            "ANSIBLE_COLLECTIONS_PATH": str(root / "cols"),
            "CALL_LOG": str(root / "calls.log"),
            "TOKEN_FILE": str(root / "token.txt"),
        })
        return subprocess.run(
            [
                "ansible-playbook",
                *extra_args,
                "-i", str(root / "inventory"),
                str(root / "playbook.yaml"),
                "-e", "ydb_bin=%s" % (root / "ydb"),
                "-e", "ydb_password=%s" % PASSWORD,
                "-e", "token_file=%s" % (root / "token.txt"),
                "-e", "result_file=%s" % (root / "result.txt"),
            ],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )


def sys_executable():
    return os.environ.get("PYTHON", sys.executable)


if __name__ == "__main__":
    unittest.main()
