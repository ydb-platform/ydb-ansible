

class YDBDCLI:
    def __init__(self, module, ydbd_bin, ca_file=None, endpoint=None, token_file=None, token=None):
        self.module = module

        self.common_options = [ydbd_bin]
        if ca_file is not None:
            self.common_options.extend(['--ca-file', ca_file])
        if endpoint is not None:
            self.common_options.extend(['--server', endpoint])
        if token is not None and token_file is not None:
            raise ValueError('must be specified only one: token or token_file')
        if token is not None:
            self.common_options.extend(['--token', token_file])
        if token_file is not None:
            self.common_options.extend(['--token-file', token_file])

    def __call__(self, cmd):
        if not isinstance(list, cmd):
            raise ValueError('cmd must be list')
        cmd = self.common_options + cmd
        return self.module.run_command(cmd)
