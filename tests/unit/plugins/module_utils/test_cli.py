import os
import sys
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
plugins_dir = os.path.join(current_dir, "../../../../plugins")
sys.path.insert(0, plugins_dir)

from module_utils.cli import YdbOps


class FakeModule:
    def __init__(self, command_result=(0, '', ''), **params):
        self.params = {
            name: spec.get('default')
            for name, spec in YdbOps.argument_spec.items()
        }
        self.params.update(params)
        self.command_result = command_result
        self.commands = []

    def run_command(self, command):
        self.commands.append(command)
        return self.command_result


class TestYdbOps(unittest.TestCase):
    def test_database_is_optional(self):
        cli = YdbOps.from_module(FakeModule(
            ydbops_bin='/tmp/ydbops',
            ydbops_endpoint='grpcs://localhost:2135',
        ))

        self.assertNotIn('--database', cli.common_options)

    def test_database_does_not_change_positional_arguments(self):
        cli = YdbOps(
            FakeModule(),
            '/tmp/ydbops',
            'grpcs://localhost:2135',
            'ydbd-storage-custom',
        )

        self.assertNotIn('--database', cli.common_options)
        unit_index = cli.common_options.index('--systemd-unit')
        self.assertEqual(cli.common_options[unit_index + 1], 'ydbd-storage-custom')

    def test_database_is_added_to_command(self):
        cli = YdbOps.from_module(FakeModule(
            ydbops_bin='/tmp/ydbops',
            ydbops_endpoint='grpcs://localhost:2135',
            database='/Root',
        ))

        database_index = cli.common_options.index('--database')
        self.assertEqual(cli.common_options[database_index + 1], '/Root')

    def test_database_is_kept_when_binary_supports_it(self):
        module = FakeModule(command_result=(0, 'Tag: v0.0.28', ''))

        database = YdbOps.compatible_database(module, '/tmp/ydbops', '/Root')

        self.assertEqual(database, '/Root')
        self.assertEqual(
            module.commands,
            [['/tmp/ydbops', '--database', '/Root', 'version']],
        )

    def test_database_is_omitted_for_old_binary(self):
        module = FakeModule(command_result=(1, 'Error: unknown flag: --database', ''))

        database = YdbOps.compatible_database(module, '/tmp/ydbops', '/Root')

        self.assertIsNone(database)

    def test_database_probe_does_not_hide_another_unknown_flag(self):
        module = FakeModule(command_result=(
            1,
            'Error: unknown flag: --other\nUsage: ydbops --database PATH',
            '',
        ))

        with self.assertRaisesRegex(RuntimeError, 'unknown flag: --other'):
            YdbOps.compatible_database(module, '/tmp/ydbops', '/Root')

    def test_database_probe_does_not_hide_mixed_output(self):
        module = FakeModule(command_result=(
            1,
            'Error: unknown flag: --database\npermission denied',
            '',
        ))

        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            YdbOps.compatible_database(module, '/tmp/ydbops', '/Root')

    def test_database_probe_does_not_hide_other_errors(self):
        module = FakeModule(command_result=(1, '', 'permission denied'))

        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            YdbOps.compatible_database(module, '/tmp/ydbops', '/Root')


if __name__ == '__main__':
    unittest.main()
