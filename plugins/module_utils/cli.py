import copy
import shlex

class CLI:
    argument_spec = None
    use_unsafe_shell = False

    def __init_subclass__(cls):
        if not isinstance(cls.argument_spec, dict):
            raise RuntimeError(f'class {cls} argument_spec is not dict')
        if 'module' in cls.argument_spec:
            raise RuntimeError(f'class {cls} argument_spec module key is reserved')

    @classmethod
    def add_arguments(cls, argument_spec):
        for key, value in cls.argument_spec.items():
            if key in argument_spec:
                if value != argument_spec[key]:
                    raise RuntimeError(f'module argument already exist: {key}, cannot override')
            else:
                argument_spec[key] = value

    @classmethod
    def from_module(cls, module, **params_override):
        params = {
            'module': module,
        }
        for key in cls.argument_spec:
            params[key] = module.params.get(key)
        params.update(params_override)
        return cls(**params)

    def __call__(self, cmd, env=None):
        if not isinstance(cmd, list):
            raise ValueError('cmd must be list')
        cmd = self.common_options + cmd
        if self.use_unsafe_shell:
            cmd_format = getattr(self, "cmd_format", "{cmd}")
            cmd = cmd_format.format(cmd=shlex.join(cmd))
        environ_update = copy.deepcopy(self.common_environ)
        if isinstance(env, dict):
            environ_update.update(env)
        self.module.log(f'calling command: {cmd}')
        return self.module.run_command(cmd, environ_update=environ_update, use_unsafe_shell=self.use_unsafe_shell)

class YDBD(CLI):
    argument_spec = dict(
        ydbd_bin=dict(type='str', default='/opt/ydb/bin/ydbd'),
        ld_library_path=dict(type='str', default='/opt/ydb/lib'),
        ca_file=dict(type='str', default=None),
        endpoint=dict(type='str', required=True),
        token=dict(type='str', default=None, no_log=True),
        token_file=dict(type='str', default=None),
    )

    def __init__(self, module, ydbd_bin, ld_library_path=None, ca_file=None, endpoint=None, token=None, token_file=None):
        self.module = module

        self.common_environ = {}
        if ld_library_path is not None:
            self.common_environ['LD_LIBRARY_PATH'] = ld_library_path

        self.common_options = [ydbd_bin]
        if ca_file is not None:
            self.common_options.extend(['--ca-file', ca_file])
        if endpoint is not None:
            self.common_options.extend(['--server', endpoint])

        if token is not None:
            self.common_environ['YDB_TOKEN'] = token
        elif token_file is not None:
            self.common_options.extend(['--token-file', token_file])


class YDB(CLI):
    argument_spec = dict(
        ydb_bin=dict(type='str', default='/opt/ydb/bin/ydb'),
        ld_library_path=dict(type='str', default='/opt/ydb/lib'),
        ca_file=dict(type='str', default=None),
        endpoint=dict(type='str', required=True),
        database=dict(type='str', required=True),
        user=dict(type='str', default=None),
        password=dict(type='str', default=None, no_log=True),
        token=dict(type='str', default=None, no_log=True),
        token_file=dict(type='str', default=None),
    )

    def __init__(self, module, ydb_bin, ld_library_path=None, ca_file=None, endpoint=None, database=None, user=None, password=None, token=None, token_file=None):
        self.module = module

        self.common_environ = {}
        if ld_library_path is not None:
            self.common_environ['LD_LIBRARY_PATH'] = ld_library_path

        self.common_options = [ydb_bin]
        if ca_file is not None:
            self.common_options.extend(['--ca-file', ca_file])
        if endpoint is not None:
            self.common_options.extend(['--endpoint', endpoint])
        if database is not None:
            self.common_options.extend(['--database', database])

        if token is not None:
            self.common_environ['YDB_TOKEN'] = token
        elif token_file is not None:
            self.common_options.extend(['--token-file', token_file])
        elif user is not None and password is not None and password != '':
            self.common_environ['YDB_USER'] = user
            self.common_environ['YDB_PASSWORD'] = password
        elif user is not None and password is not None and password == '':
            self.common_options.extend(['--user', user])
            self.common_options.extend(['--no-password', token_file])


class DsTool(CLI):
    argument_spec = dict(
        dstool_bin=dict(type='str', default='/opt/ydb/bin/ydb-dstool'),
        endpoint=dict(type='str', required=True),
        ca_file=dict(type='str', default=None),
        token=dict(type='str', default=None, no_log=True),
        token_file=dict(type='str', default=None)
    )

    def __init__(self, module, dstool_bin, endpoint, ca_file=None, token=None, token_file=None):
        self.module = module

        self.common_options = [dstool_bin]
        self.common_environ = {}

        if endpoint is not None:
            self.common_options.append(f'--endpoint={endpoint}')
            if endpoint.startswith('http'):
                self.common_options.append('--http')
        if ca_file is not None:
            self.common_options.extend(['--ca-file', ca_file])
        if token is not None:
            self.common_environ['YDB_TOKEN'] = token
        elif token_file is not None:
            self.common_options.extend(['--token-file', token_file])


class YdbOps(CLI):
    argument_spec = dict(
        ydbops_bin=dict(type='str', default=None),
        ydbops_endpoint=dict(type='str', default=None),
        ydbops_systemd_unit=dict(type='str', default='ydbd-storage'),
        ca_file=dict(type='str', default=None),
        ssh_args=dict(type='str', default=None),
        availability_mode=dict(type='str', default='strong'),
        token=dict(type='str', default=None, no_log=True),
        token_file=dict(type='str', default=None),
        hosts=dict(type='str',default=None),
        log=dict(type='bool',default=False),
        logfile=dict(type='str',default=None),
    )

    def __init__(self, module, ydbops_bin, ydbops_endpoint, ydbops_systemd_unit=None,
                 ca_file=None, ssh_args=None, availability_mode=None, token=None, token_file=None, hosts=None, log=False, logfile=None):
        self.module = module

        self.common_options = [ydbops_bin, 'restart', '--storage']
        self.common_environ = {}

        if ydbops_endpoint is not None:
            self.common_options.extend(['--endpoint', ydbops_endpoint])
        if ca_file is not None:
            self.common_options.extend(['--ca-file', ca_file])
        if ssh_args is not None:
            self.common_options.extend(['--ssh-args', ssh_args])
        if ydbops_systemd_unit is not None:
            self.common_options.extend(['--systemd-unit', ydbops_systemd_unit])
        if availability_mode is not None:
            self.common_options.extend(['--availability-mode', availability_mode])
        if hosts is not None:
            self.common_options.extend(['--hosts',hosts])
        if token is not None:
            self.common_environ['YDB_TOKEN'] = token
        elif token_file is not None:
            self.common_options.extend(['--token-file', token_file])
        if log and logfile is not None:
            self.cmd_format = "{cmd} >> " + shlex.quote(logfile)
            self.use_unsafe_shell = True