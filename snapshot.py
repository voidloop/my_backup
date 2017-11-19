#!/usr/bin/env python
# coding: utf-8

#
# mem - 2017/06/08
# marco.esposito@roma1.infn.it
#

from __future__ import print_function
from subprocess import call
import os, sys

#-------------------------------------------------------------------------------
class SnapshotArchive:
    def __init__(self, base, name="snapshot", count=3):
        self.base = base
        self.name = name
        self.count = count

    def dir(self, suffix):
        return "%s/%s.%d" % (self.base, self.name, suffix)

#-------------------------------------------------------------------------------
class ToolError(Exception):
    pass

#-------------------------------------------------------------------------------
def errmsg(*args, **kargs):
    print(sys.argv[0], file=sys.stderr, end=": ")
    print(*args, file=sys.stderr, **kargs)

#-------------------------------------------------------------------------------
def rotate(archive, upto=0):
    oldest = archive.count - 1
    
    # step 1: delete the oldest snapshot, if it exists:
    if os.path.isdir(archive.dir(oldest)):
        if call(["rm", "-rf", archive.dir(oldest)]) != 0:
            raise ToolError("rotate: rm failed")

    # step 2: shift the middle snapshot(s) back by one, it they exist
    for x in range(oldest, upto, -1):
        if os.path.isdir(archive.dir(x-1)):
            if call(["mv", archive.dir(x-1), archive.dir(x)]) != 0:
                raise ToolError("rotate: mv failed")

    return True

#-------------------------------------------------------------------------------
def hardlink(source, dest, create=False):
    # step 3: make a hard-link-only (except for dirs) 
    # copy of the latest snapshot
    if os.path.isdir(source):
        if call(["cp", "-al", source, dest]) != 0:
            raise ToolError("hardlink: cp failed")
    elif create:
        if call(["mkdir", "-p", source]) != 0:
            raise ToolError("hardlink: mkdir failed")

#-------------------------------------------------------------------------------
def rsync(source, dest, exclude=[]):
    # prepare exclude arguments
    exclude = list(map(lambda x: "--exclude=%s" % x, exclude))

    # step 4: rsync from the system into the latest snapshot (notice that
    # rsync behaves like cp --remove-destination by default, so the 
    # destination is unlinked first.  If it were not so, this would copy 
    # over the other snapshot(s) too!
    retcode = call(["rsync", "-va", "--delete", "--delete-excluded"]
        + exclude + source + [dest])
    if retcode not in (0, 23): 
        raise ToolError("rsync: rsync failed (exit value: %d)" % retcode)
    
    # step 5: update the mtime of snapshot.0 to reflect the snapshot time
    if call(["touch", dest]) != 0:
        raise ToolError("rsync: touch failed")

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    source = [ os.environ["HOME"] ] 
    archive = SnapshotArchive("/tmp", name="daily", count=10)

    # make sure we're running as root
    #if os.getuid() != 0:
    #    errmsg("sorry, must be root. Exiting...")
    #    sys.exit(1)

    # attempt to remount the RW mount point as RW; else abort
    #if call(["mount", "-o remount,rw", device, mountpoint]) != 0:
    #    errmsg("mount failed")
    #    sys.exit(1)

    # make a snapshot
    try:
        # rotating snapshots 
        rotate(archive, upto=1)
        # make a hard-link-only copy of the latest snapshot
        hardlink(archive.dir(0), archive.dir(1), create=True)
        # rsync from the system into the latest snapshot 
        rsync(source, archive.dir(0))

    except ToolError as e: 
        errmsg(e)
        sys.exit(1)

    finally:
        # now remount the RW snapshot mountpoint as readonly
        #call(["mount", "-o remount,ro", device, mountpoint]):
        pass

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

# a)    make sure we're running as root
#
# b)    attempt to remount the RW mount point as RW; else abort
#
# 1)    delete the oldest snapshot (n), if it exists: 
#           
#           rm -rf dir.n
#
# 2)     shift the middle snapshots back by one, it they exist: 
#       
#           mv dir.(x-1) dir.x, for x = n, n-1, ..., 2
#
# 3)    make a hard-link-only copy of the latest snapshot:
#
#           cp -al dir.0 -> dir.1
#
# 4)    rsync from the system into the latest snapshot: 
#
#           rsync -a --del source dir.0
#
# c)    remount the RW snapshot mountpoint as readonly



