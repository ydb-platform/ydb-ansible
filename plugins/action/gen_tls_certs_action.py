from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        
        display = Display()
        display.v("Running ydb_platform.ydb.gen_tls_certs module")

        module_args = self._task.args.copy()
        module_result = self._execute_module(
            module_name='ydb_platform.ydb.gen_tls_certs',
            module_args=module_args,
            task_vars=task_vars,
            tmp=tmp
        )

        # Merge the module result into the action result
        result.update(module_result)
        
        return result