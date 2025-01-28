import os
import stat
import shutil


LABEL_DIR = '/dev/disk/by-partlabel'


def is_block_device(path):
    mode = os.stat(path).st_mode
    return stat.S_ISBLK(mode)

def create_partition_if_not_exists(module, name, label):
    changed = False
    label_path = os.path.join(LABEL_DIR, label)
    if os.path.exists(label_path):
        return changed, label_path
    changed = True
    parted_bin = shutil.which('parted')
    partprobe_bin = shutil.which('partprobe')
    sgdisk_bin = shutil.which('sgdisk')
    if parted_bin is not None and partprobe_bin is not None and not os.path.exists("/etc/altlinux-release"):
        changed = create_partition_parted(module, name, label, parted_bin, partprobe_bin)
    elif sgdisk_bin is not None:
        changed = create_partition_sgdisk(module, name, label, sgdisk_bin)
    else:
        raise RuntimeError('failed to find parted or sgdisk binary in PATH')
    return changed, label_path


def create_partition_parted(module, name, label, parted_bin, partprobe_bin):
    module.run_command([parted_bin, '--script', name, 'mklabel', 'gpt'])
    module.run_command([parted_bin, '--script', name, 'mkpart', label, '0%', '100%', '--align', 'optimal'])
    module.run_command([partprobe_bin, name])


def create_partition_sgdisk(module, name, label, sgdisk_bin):
    module.run_command([sgdisk_bin, '--clear', name])
    module.run_command([sgdisk_bin, '--new=1:2048:0', name])
    module.run_command([sgdisk_bin, f'--change-name=1:{label}', name])


def prepare_partition_using_dd(module, label_path):
    dd_bin = shutil.which('dd')
    module.run_command([dd_bin, 'if=/dev/zero', f'of={label_path}', 'bs=1M', 'count=1', 'status=none'])


def check_if_disk_was_obliterated(module, label_path):
    dd_bin = shutil.which('dd')
    expected_value = '3a3ed164e42500a1c5b2d0093f0a813d27dc50d038f330cc100a7e70ece2e6e4'
    rc, actual_value, _ = module.run_command(f'{dd_bin} if={label_path} bs=1024 count=96 status=none | sha256sum | (read x y && echo $x)', use_unsafe_shell=True)
    if rc != 0:
        raise RuntimeError('failed to check if disk was obliterated')
    return expected_value == actual_value
