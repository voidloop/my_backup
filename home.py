#!/usr/bin/python3

from archive import Backup, SudoMount
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
    source = [home + '/']

    try:
        with SudoMount(device, dest):
            backup = Backup(source, dest, exclude=exclude, maxcount=20)

            notify('Backup started')
            time_start = time.time()

            backup.run()

            elapsed_time = time.time() - time_start
            notify('Backup finished (%.1f s)' % elapsed_time)

    except Exception as err:
        notify('Backup failed: ' + str(err))



