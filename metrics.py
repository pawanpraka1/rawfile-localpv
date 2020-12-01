import json
import os
import subprocess

from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily

import rawfile_util
from rawfile_util import attached_loops


def path_stats(path):
    fs_stat = os.statvfs(path)
    return {
        "fs_size": fs_stat.f_frsize * fs_stat.f_blocks,
        "fs_free": fs_stat.f_frsize * fs_stat.f_bfree,
        "fs_files": fs_stat.f_files,
        "fs_files_free": fs_stat.f_ffree,
    }


def volume_stats(volume_id: str) -> dict:
    img_file = rawfile_util.img_file(volume_id)
    dev_stat = img_file.stat()
    stats = {
        "dev_size": dev_stat.st_size,
        "dev_free": dev_stat.st_size - dev_stat.st_blocks * 512,
    }
    mountpoint = volume_to_mountpoint(img_file)
    if mountpoint is not None:
        stats.update(path_stats(mountpoint))
    return stats


class VolumeStatsCollector(object):
    def collect(self):
        VOLUME_ID = "volume_id"
        fs_size = GaugeMetricFamily(
            "rawfile_filesystem_size_bytes",
            "Filesystem size in bytes.",
            labels=[VOLUME_ID],
        )
        fs_free = GaugeMetricFamily(
            "rawfile_filesystem_avail_bytes",
            "Filesystem free space in bytes",
            labels=[VOLUME_ID],
        )
        fs_files = GaugeMetricFamily(
            "rawfile_filesystem_files",
            "Filesystem total file nodes.",
            labels=[VOLUME_ID],
        )
        fs_files_free = GaugeMetricFamily(
            "rawfile_filesystem_files_free",
            "Filesystem total free file nodes",
            labels=[VOLUME_ID],
        )
        dev_size = GaugeMetricFamily(
            "rawfile_device_size_bytes", "Device size in bytes.", labels=[VOLUME_ID]
        )
        dev_free = GaugeMetricFamily(
            "rawfile_device_free_bytes",
            "Device free space in bytes.",
            labels=[VOLUME_ID],
        )

        for volume_id in rawfile_util.list_all_volumes():
            labels = [volume_id]
            key_to_gauge = {
                "dev_size": dev_size,
                "dev_free": dev_free,
                "fs_size": fs_size,
                "fs_free": fs_free,
                "fs_files": fs_files,
                "fs_files_free": fs_files_free,
            }
            stats = volume_stats(volume_id)
            for key in stats.keys():
                key_to_gauge[key].add_metric(labels, stats[key])

        return [fs_size, fs_free, fs_files, fs_files_free, dev_size, dev_free]


def volume_to_mountpoint(img_file):
    for dev in attached_loops(img_file):
        mountpoint = dev_to_mountpoint(dev)
        if mountpoint is not None:
            return mountpoint
    return None


def dev_to_mountpoint(dev_name):
    try:
        output = subprocess.run(
            f"findmnt --json --first-only {dev_name}",
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode()
        data = json.loads(output)
        return data["filesystems"][0]["target"]
    except subprocess.CalledProcessError:
        return None


def mountpoint_to_dev(mountpoint):
    res = subprocess.run(
        f"findmnt --json --first-only --mountpoint {mountpoint}",
        shell=True,
        capture_output=True,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout.decode().strip())
    return data["filesystems"][0]["source"]


def expose_metrics():
    REGISTRY.register(VolumeStatsCollector())
    start_http_server(9100)
