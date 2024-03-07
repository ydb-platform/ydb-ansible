from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash
from ansible.utils.display import Display


display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)

        allow_format = self._task.args['allow_format']
        if allow_format:
            display.warning('RISK OF DATA LOSS: "allow_format" is set to True: this may cause data loss if not handled with care!')

        results = merge_hash(
            results,
            self._execute_module(
                module_name='ydb_platform.ydb.drive_prepare',
                tmp=tmp,
                task_vars=task_vars,
            )
        )
        return results
