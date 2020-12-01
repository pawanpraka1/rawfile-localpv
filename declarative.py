import os
import subprocess
from pathlib import Path

from util import run


def be_absent(path):
    path = Path(path)
    if not path.exists():
        return
    elif path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        path.rmdir()
        # XXX: should we `shutil.rmtree(path)` instead?
    else:
        raise Exception("Unknown file type")


def be_symlink(path, to):
    path = Path(path)
    to = Path(to)
    if path.exists():
        if path.is_symlink():
            if os.readlink(path) == str(to):
                return
        be_absent(path)
    path.symlink_to(to)


def be_mounted(dev, mountpoint):
    dev = Path(dev).resolve()
    mountpoint = Path(mountpoint)

    if mountpoint.is_mount():
        if True:  # TODO: verify that the right device is mounted
            return
        # noinspection PyUnreachableCode
        be_unmounted(mountpoint)

    run(f"mount {dev} {mountpoint}")


def be_unmounted(path):
    path = Path(path)
    while path.is_mount():
        run(f"umount {path}")


def current_fs(device):
    res = subprocess.run(
        f"blkid -o value -s TYPE {device}", shell=True, capture_output=True
    )
    if res.returncode == 2:  # specified token was not found
        return None
    return res.stdout.decode().strip()


def be_formatted(dev, fs):
    def init_fs(device, filesystem):
        if fs == "ext4":
            run(f"mkfs.ext4 {device}")
        elif fs == "btrfs":
            run(f"mkfs.btrfs {device}")
        else:
            raise Exception(f"Unsupported fs type: {filesystem}")

    dev = Path(dev).resolve()
    current = current_fs(dev)
    if current is None:
        init_fs(dev, fs)
    else:
        if current != fs:
            raise Exception(f"Existing filesystem does not match: {current}/{fs}")


def be_fs_expanded(fs, dev, path):
    dev = Path(dev).resolve()
    path = Path(path).resolve()
    if fs == "ext4":
        run(f"resize2fs {dev}")
    elif fs == "btrfs":
        run(f"btrfs filesystem resize max {path}")
    else:
        raise Exception(f"Unsupported fsType: {fs}")
