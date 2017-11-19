#!/usr/bin/env python
# coding: utf-8

#
# mem - 2017/11/18
# marco.esposito@gmail.com
#

from __future__ import print_function
from subprocess import call
from snapshot import *
import os, sys
import time
from pydbus import SessionBus

#-------------------------------------------------------------------------------
def notify(message):
    bus = SessionBus()
    notifier = bus.get(".Notifications")
    notifier.Notify("home.py", 0, "", "My backup", message, "", "", 10000)

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    # configuration 
    home = os.environ["HOME"]
    device = "UUID=4d29d023-ed3a-40d7-8855-f63c1ec803ce"
    mountpoint = home + "/.backup/backupdisk.d"
    exclude = [ "/.backup/backupdisk.*", "/.cache/", "/.mozilla/"]
    source = [ home + "/" ] 

    archive = SnapshotArchive(mountpoint, name="snapshot", count=36)

    # flag to notify if backup was completed with success or error
    backup_success = False

    # if backup was completed with success, notify elapsed time
    time_start = time.time()
    notify("Backup started")

    # attempt to remount the RW mount point as RW; else abort
    if call(["sudo", "mount", device, mountpoint]) != 0:
        notify("Error: mount failed")
        errmsg("mount failed")
        sys.exit(1)
   
    try:
        # rotating snapshots 
        rotate(archive, upto=1)

        # make a hard-link-only copy of the latest snapshot 
        # or create dir.0 if it doesn't exist
        hardlink(archive.dir(0), archive.dir(1), create=True)

        # rsync from the system into the latest snapshot 
        rsync(source, archive.dir(0), exclude)
        
        backup_success = True

    except ToolError as e: 
        errmsg(e)
        sys.exit(1)

    finally:
        if backup_success: 
            elapsed = time.time() - time_start
            notify("Backup finished: success (%.1f s)" % elapsed)
        else: 
            notify("Error: backup failed")


        # now remount the RW snapshot mountpoint as readonly
        if call(["sudo", "umount", mountpoint]) != 0:
            notify("Error: umount failed")
            errmsg("umount failed")
            sys.exit(1)
