from subprocess import Popen, PIPE
import os


class CommandError(Exception):
    pass


class ArchiveError(Exception):
    pass


def _exec(args):
    with Popen(args, stderr=PIPE) as proc:
        _, error = proc.communicate()
        if proc.returncode != 0:
            raise CommandError(error.decode('utf-8').strip())


class SnapshotBackup:
    def __init__(self, sources, archive, exclude=None):
        self.sources = sources
        self.archive = archive
        self.exclude = exclude or []

    def run(self):
        # rotate snapshots, from the oldest up to the one with suffix 1
        self._shift(upto=1)

        # make a hard-link-only copy of the latest snapshot
        if self.archive.exists(0):
            self.archive.copy(0, 1)

        # rsync from the system into the latest snapshot
        self._rsync(self.archive.dir(0))

    def _shift(self, upto=0):
        last = self.archive.maxcount-1

        if self.archive.exists(last):
            self.archive.delete(last)

        for suffix in range(last, upto, -1):
            if self.archive.exists(suffix-1):
                self.archive.move(suffix-1, suffix)

    def _rsync(self, dest):
        # prepare exclude arguments
        exclude_args = ['--exclude={}'.format(x) for x in self.exclude]

        # rsync from the system into the latest snapshot
        _exec(['/usr/bin/rsync', '--archive', '--delete', '--delete-excluded'] + exclude_args + self.sources + [dest])

        # update the mtime of snapshot.0 to reflect the snapshot time
        _exec(['/usr/bin/touch', dest])


class Archive:
    def __init__(self, base, subdir="snapshot", maxcount=7):
        if not os.path.exists(base):
            raise ArchiveError("{} doesn't exist".format(base))

        if not os.path.isdir(base):
            raise ArchiveError('{} is not a directory'.format(base))

        self.base = base
        self.subdir = subdir
        self.maxcount = maxcount

    def compact(self):
        target = 0
        for suffix in range(self.maxcount):
            if self.exists(suffix):
                if suffix != target:
                    self.move(suffix, target)
                target = target + 1

    def move(self, source, dest):
        self._raise_error_if_exists(dest)
        _exec(['/bin/mv', self.dir(source), self.dir(dest)])

    def delete(self, suffix):
        _exec(['/bin/rm', '--recursive', '--force', self.dir(suffix)])

    def copy(self, source, dest):
        self._raise_error_if_exists(dest)
        _exec(['/bin/cp', '--archive', '--link', self.dir(source), self.dir(dest)])

    def exists(self, suffix):
        return os.path.isdir(self.dir(suffix))

    def dir(self, suffix):
        return '{}/{}.{}'.format(self.base, self.subdir, suffix)

    def _raise_error_if_exists(self, suffix):
        if self.exists(suffix):
            raise ArchiveError('{} already exists'.format(self.dir(suffix)))


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
        _exec(args)


class SudoMount(Mount):
    @staticmethod
    def _exec(args):
        Mount._exec(['sudo'] + args)
