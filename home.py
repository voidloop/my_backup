#!/usr/bin/python3
from backup import SnapshotBackup, SudoMount, Archive
from pydbus import SessionBus
import os
import time


def notify(message):
    bus = SessionBus()
    notifier = bus.get(".Notifications")
    notifier.Notify("home.py", 0, "", "My backup", message, "", "", 10000)


if __name__ == '__main__':
    home = os.environ['HOME']
    device = 'UUID=4d29d023-ed3a-40d7-8855-f63c1ec803ce'
    dest = home + '/.backup/backupdisk.d'
    exclude = ['/.backup/backupdisk.*', '/.cache/', '/.mozilla/']
    sources = [home + '/']

    try:
        with SudoMount(device, dest):
            archive = Archive(dest, maxcount=20)
            backup = SnapshotBackup(sources, archive, exclude=exclude)

            notify('Backup started')
            time_start = time.time()

            archive.compact()
            backup.run()

            elapsed_time = time.time() - time_start
            notify('Backup finished (%.1f s)' % elapsed_time)

    except Exception:
        notify('Backup failed!')
        raise
