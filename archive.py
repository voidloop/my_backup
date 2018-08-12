from subprocess import Popen, PIPE
import glob
import os


class ExecError(Exception):
    pass


def _exec(args):
    with Popen(args, stderr=PIPE) as proc:
        _, error = proc.communicate()
        if proc.returncode != 0:
            raise ExecError(error.decode('utf-8').strip())


class BackupError(Exception):
    pass


class Backup:
    def __init__(self, source, dest, maxcount=7, exclude=None):
        self.source = source
        self.archive = SnapshotArchive(dest, maxcount=maxcount)
        self.exclude = exclude or []

    def run(self):
        # rotate snapshots, from the oldest up to the one with suffix 1
        self.archive.shift(upto=1)

        # make a hard-link-only copy of the latest snapshot
        if self.archive.exists(0):
            self._hardlink(self.archive.dir(0), self.archive.dir(1))

        # rsync from the system into the latest snapshot
        self._rsync(self.archive.dir(0))

    def _rsync(self, dest):
        # prepare exclude arguments
        exclude_args = ['--exclude={}'.format(x) for x in self.exclude]

        # rsync from the system into the latest snapshot
        self._exec(['rsync', '-a', '--delete', '--delete-excluded'] + exclude_args + self.source + [dest])

        # update the mtime of snapshot.0 to reflect the snapshot time
        self._exec(["touch", dest])

        self.archive.purge()

    @staticmethod
    def _hardlink(src, dst):
        Backup._exec(["cp", "-al", src, dst])

    @staticmethod
    def _exec(args):
        try:
            _exec(args)
        except ExecError as err:
            raise BackupError(err)


class ArchiveError(Exception):
    pass


class SnapshotArchive:
    def __init__(self, base, subdir="snapshot", maxcount=7):
        if not os.path.exists(base):
            raise ArchiveError("{} doesn't exist".format(base))

        if not os.path.isdir(base):
            raise ArchiveError('{} is not a directory'.format(base))

        self.base = base
        self.subdir = subdir
        self.maxcount = maxcount

    def dir(self, suffix):
        return "%s/%s.%d" % (self.base, self.subdir, suffix)

    def exists(self, suffix):
        return os.path.isdir(self.dir(suffix))

    def shift(self, upto=0):
        oldest = self.maxcount-1
        self._delete_if_exists(oldest)

        for suffix in range(oldest, upto, -1):
            self._move_if_exists(suffix-1, suffix)

    def purge(self):
        files_to_remove = set(glob.glob('{}/*'.format(self.base)))
        files_to_preserve = {self.dir(x) for x in range(self.maxcount)}
        for item in files_to_remove - files_to_preserve:
            self._exec(['rm', '-rf', item])

    def compact(self):
        target = 0
        for suffix in range(self.maxcount):
            if self.exists(suffix):
                if suffix != target:
                    self._move_if_exists(suffix, target)
                target = target + 1

    def _move_if_exists(self, source, dest):
        if self.exists(source):
            self._exec(['mv', self.dir(source), self.dir(dest)])

    def _delete_if_exists(self, suffix):
        if self.exists(suffix):
            self._exec(['rm', '-rf', self.dir(suffix)])

    @staticmethod
    def _exec(args):
        try:
            _exec(args)
        except ExecError as err:
            raise ArchiveError(err)


class MountError(Exception):
    pass


class Mount:
    def __init__(self, device, mount_dir):
        self._device = device
        self._dir = mount_dir

    def __enter__(self):
        self._exec(['mount', self._device, self._dir])

    def __exit__(self, *args):
        self._exec(['umount', self._dir])

    @staticmethod
    def _exec(args):
        try:
            _exec(args)
        except ExecError as err:
            raise MountError(err)


class SudoMount(Mount):
    @staticmethod
    def _exec(args):
        Mount._exec(['sudo'] + args)
