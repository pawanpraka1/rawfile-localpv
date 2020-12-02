import glob
import json
from os.path import basename, dirname
from pathlib import Path

from consts import DATA_DIR
from volume_schema import migrate_to, LATEST_SCHEMA_VERSION
from util import run, run_out


def img_dir(volume_id):
    return Path(f"{DATA_DIR}/{volume_id}")


def meta_file(volume_id):
    return Path(f"{img_dir(volume_id)}/disk.meta")


def metadata(volume_id):
    try:
        return json.loads(meta_file(volume_id).read_text())
    except FileNotFoundError:
        return {}


def lv_path(volume_id):
    return Path(metadata(volume_id)["lv_path"])


def update_metadata(volume_id: str, obj: dict) -> dict:
    meta_file(volume_id).write_text(json.dumps(obj))
    return obj


def patch_metadata(volume_id: str, obj: dict) -> dict:
    old_data = metadata(volume_id)
    new_data = {**old_data, **obj}
    return update_metadata(volume_id, new_data)


def migrate_metadata(volume_id, target_version):
    old_data = metadata(volume_id)
    new_data = migrate_to(old_data, target_version)
    return update_metadata(volume_id, new_data)


def attached_loops(file: str) -> [str]:
    out = run_out(f"losetup -j {file}").stdout.decode()
    lines = out.splitlines()
    devs = [line.split(":", 1)[0] for line in lines]
    return devs


def attach_loop(file) -> str:
    def next_loop():
        loop_file = run_out(f"losetup -f").stdout.decode().strip()
        if not Path(loop_file).exists():
            pfx_len = len("/dev/loop")
            loop_dev_id = loop_file[pfx_len:]
            run(f"mknod {loop_file} b 7 {loop_dev_id}")
        return loop_file

    while True:
        devs = attached_loops(file)
        if len(devs) > 0:
            return devs[0]
        next_loop()
        run(f"losetup --direct-io=on -f {file}")


def detach_loops(file) -> None:
    devs = attached_loops(file)
    for dev in devs:
        run(f"losetup -d {dev}")


def list_all_volumes():
    metas = glob.glob(f"{DATA_DIR}/*/disk.meta")
    return [basename(dirname(meta)) for meta in metas]


def migrate_all_volume_schemas():
    target_version = LATEST_SCHEMA_VERSION
    for volume_id in list_all_volumes():
        migrate_metadata(volume_id, target_version)
