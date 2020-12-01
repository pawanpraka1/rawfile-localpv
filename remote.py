from util import remote_fn


@remote_fn
def scrub(volume_id):
    import time
    import rawfile_util

    rawfile_util.patch_metadata(volume_id, {"deleted_at": time.time()})


@remote_fn
def init_rawfile(volume_id, size):
    import time
    import rawfile_util
    from volume_schema import LATEST_SCHEMA_VERSION
    from pathlib import Path

    from util import run

    img_dir = rawfile_util.img_dir(volume_id)
    img_dir.mkdir(exist_ok=True)
    vg_name = "vg-test"  # FIXME
    lv_path = Path(f"/dev/{vg_name}/{volume_id}")  # TODO: use lv_uuid instead of path
    if lv_path.exists():
        return
    rawfile_util.patch_metadata(
        volume_id,
        {
            "schema_version": LATEST_SCHEMA_VERSION,
            "volume_id": volume_id,
            "created_at": time.time(),
            "lv_path": lv_path.as_posix(),
            "size": size,
        },
    )
    run(f"lvcreate {vg_name} --name {volume_id} --size {size}b")


@remote_fn
def expand_rawfile(volume_id, size):
    import rawfile_util
    from util import run

    lv_path = rawfile_util.lv_path(volume_id)
    if rawfile_util.metadata(volume_id)["size"] >= size:
        return
    rawfile_util.patch_metadata(
        volume_id, {"size": size},
    )
    run(f"lvextend {lv_path} --size {size}b")
