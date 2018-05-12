#!/usr/bin/env python3
import hashlib
import logging
import os
from argparse import ArgumentParser
from itertools import zip_longest
from os.path import realpath, isdir, isfile, join, islink, getsize

logger = logging.getLogger('main')

RED = 31
GREEN = 32
YELLOW = 33


def main():
    parser = ArgumentParser()
    parser.add_argument('-f', action='store_true', help='Follow symlink')
    parser.add_argument('-d', '--depth', default=None, type=int)
    parser.add_argument('--checksum', action='store_true')
    parser.add_argument('-o', '--output', default=None)
    parser.add_argument('dir1', type=resolve_dir)
    parser.add_argument('dir2', type=resolve_dir)
    args = parser.parse_args()

    if args.output:
        handler = logging.FileHandler(args.output, mode='w')
        colored = lambda msg, color: msg
    else:
        handler = logging.StreamHandler()
        colored = lambda msg, color: '\033[%dm%s\033[39m' % (color, msg)

    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

    for a, b in zip_files(args.dir1, args.dir2, follow=args.f, depth=args.depth):
        if not a:
            logger.error(colored('+ %s' % b, GREEN))
        elif not b:
            logger.error(colored('- %s' % a, RED))
        elif getsize(a) != getsize(b) \
                or (args.checksum and md5sum(a) != md5sum(b)):
            logger.error(colored('* %s' % b, YELLOW))


def resolve_dir(path):
    assert isdir(path), '%s must be directory' % path
    return realpath(path)


def zip_files(dir1, dir2, follow=False, depth=-1):
    files1 = set(os.listdir(dir1))
    files2 = set(os.listdir(dir2))

    for filename in sorted(files1 | files2):
        file1 = join(dir1, filename)
        file2 = join(dir2, filename)
        zipped_walk_f1 = zip_longest(walk(file1, follow, depth), [],
                                     fillvalue=None)
        zipped_walk_f2 = zip_longest([], walk(file2, follow, depth),
                                     fillvalue=None)

        if filename not in files2:
            yield from zipped_walk_f1

        elif filename not in files1:
            yield from zipped_walk_f2

        elif (isfile(file1) and isfile(file2)) or (isdir(file1) and isdir(file2)):

            if islink(file1):
                if not follow:
                    logger.warning('%s is symlink', file1)
                    file1 = None
                else:
                    logger.debug('%s is symlink', file1)

            if islink(file2):
                if not follow:
                    logger.warning('%s is symlink', file2)
                    file2 = None
                else:
                    logger.debug('%s is symlink', file2)

            if file1 and file2:
                if isfile(file1):
                    yield file1, file2
                else:
                    yield from zip_files(file1, file2, follow)
            elif file1:
                yield from zipped_walk_f1
            elif file2:
                yield from zipped_walk_f2

        else:
            yield from zipped_walk_f1
            yield from zipped_walk_f2


def walk(path, follow=False, depth=None):
    if depth is not None:
        depth -= 1
    if not follow and islink(path):
        logger.warning('%s is symlink', path)
        return []
    yield path
    if depth is None or depth > 0 and isdir(path):
        for filename in sorted(os.listdir(path)):
            yield from walk(join(path, filename), follow, depth)


def md5sum(file):
    md5 = hashlib.md5()
    with open(file, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
