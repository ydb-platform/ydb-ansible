from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleError
from ansible.playbook.conditional import Conditional
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display


display = Display()


class ActionModule(ActionBase):
    _requires_connection = False

    _VALID_ARGS = frozenset(('msg', 'that'))

    def run(self, tmp=None, task_vars=None):
        if 'msg' not in self._task.args:
            raise AnsibleError('message required in "msg" argument')

        if 'that' not in self._task.args:
            raise AnsibleError('conditional required in "that" string')

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        msg = self._task.args['msg']

        thats = self._task.args['that']
        if not isinstance(thats, list):
            thats = [thats]

        cond = Conditional(loader=self._loader)

        for that in thats:
            cond.when = [that]
            test_result = cond.evaluate_conditional(templar=self._templar, all_vars=task_vars)
            if test_result:
                display.warning(msg)

        result['failed'] = False
        result['changed'] = False
        return result
