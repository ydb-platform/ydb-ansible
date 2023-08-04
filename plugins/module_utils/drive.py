import os
import stat
import shutil


LABEL_DIR = '/dev/disk/by-partlabel'


def is_block_device(path):
    mode = os.stat(path).st_mode
    return stat.S_ISBLK(mode)


def create_partition_if_not_exists(module, name, label):
    label_path = os.path.join(LABEL_DIR, label)
    if os.path.exists(label_path):
        return False

    parted_bin = shutil.which('parted')
    partprobe_bin = shutil.which('partprobe')
    sgdisk_bin = shutil.which('sgdisk')
    dd_bin = shutil.which('dd')
    if parted_bin is not None and partprobe_bin is not None:
        create_partition_parted(module, name, label, parted_bin, partprobe_bin)
    elif sgdisk_bin is not None:
        create_partition_sgdisk(module, name, label, sgdisk_bin)
    else:
        raise RuntimeError('failed to find parted or sgdisk binary in PATH')

    fill_zeros(module, label_path, dd_bin)

    return True


def create_partition_parted(module, name, label, parted_bin, partprobe_bin):
    module.run_command([parted_bin, name, 'mklabel', 'gpt', '-s'])
    module.run_command([parted_bin, '-a', 'optimal', name, 'mkpart', 'primary', '0%', '100%'])
    module.run_command([parted_bin, name, '1', label])
    module.run_command([partprobe_bin, name])

def create_partition_sgdisk(module, name, label, sgdisk_bin):
    module.run_command([sgdisk_bin, '-o', name])
    module.run_command([sgdisk_bin, '-n', '1:2048:0', name])
    module.run_command([sgdisk_bin, '-n', f'1:{label}', name])


def fill_zeros(module, label_path, dd_bin):
    module.run_command([dd_bin, 'if=/dev/zero', f'of={label_path}', 'bs=1M', 'count=1', 'status=none'])
