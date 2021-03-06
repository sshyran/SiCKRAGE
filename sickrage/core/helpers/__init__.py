# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import base64
import ctypes
import datetime
import io
import os
import platform
import random
import re
import shutil
import socket
import stat
import string
import sys
import tempfile
import time
import traceback
import urlparse
import uuid
import webbrowser
import zipfile
from collections import OrderedDict
from contextlib import contextmanager

import rarfile
import requests
import six
from bs4 import BeautifulSoup

import sickrage
from sickrage.core.common import Quality, SKIPPED, WANTED
from sickrage.core.exceptions import MultipleShowObjectsException

mediaExtensions = [
    'avi', 'mkv', 'mpg', 'mpeg', 'wmv',
    'ogm', 'mp4', 'iso', 'img', 'divx',
    'm2ts', 'm4v', 'ts', 'flv', 'f4v',
    'mov', 'rmvb', 'vob', 'dvr-ms', 'wtv',
    'ogv', '3gp', 'webm', 'tp'
]


def safe_getattr(object, name, default=None):
    try:
        return getattr(object, name, default)
    except:
        return default


def try_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def readFileBuffered(filename, reverse=False):
    blocksize = (1 << 15)
    with io.open(filename, 'r', encoding='utf-8') as fh:
        if reverse:
            fh.seek(0, os.SEEK_END)
        pos = fh.tell()
        while True:

            if reverse:
                chunksize = min(blocksize, pos)
                pos -= chunksize
            else:
                chunksize = max(blocksize, pos)
                pos += chunksize

            fh.seek(pos, os.SEEK_SET)
            data = fh.read(chunksize)
            if not data:
                break
            yield data
            del data


def argToBool(x):
    """
    convert argument of unknown type to a bool:
    """

    if isinstance(x, six.string_types):
        if x.lower() in ("0", "false", "f", "no", "n", "off"):
            return False
        elif x.lower() in ("1", "true", "t", "yes", "y", "on"):
            return True
        raise ValueError("failed to cast as boolean")

    return bool(x)


def auto_type(s):
    for fn in (int, float, argToBool):
        try:
            return fn(s)
        except ValueError:
            pass

    return (s, '')[s.lower() == "none"]


def fixGlob(path):
    path = re.sub(r'\[', '[[]', path)
    return re.sub(r'(?<!\[)\]', '[]]', path)


def indentXML(elem, level=0):
    """
    Does our pretty printing, makes Matt very happy
    """
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indentXML(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def remove_extension(name):
    """
    Remove download or media extension from name (if any)
    """

    if name and "." in name:
        base_name, sep, extension = name.rpartition('.')
        if base_name and extension.lower() in ['nzb', 'torrent'] + mediaExtensions:
            name = base_name

    return name


def remove_non_release_groups(name):
    """
    Remove non release groups from name
    """
    if not name:
        return name

    # Do not remove all [....] suffixes, or it will break anime releases ## Need to verify this is true now
    # Check your database for funky release_names and add them here, to improve failed handling, archiving, and history.
    # select release_name from tv_episodes WHERE LENGTH(release_name);
    # [eSc], [SSG], [GWC] are valid release groups for non-anime
    removeWordsList = OrderedDict([
        (r'^\[www\.Cpasbien\.pe\] ', 'searchre'),
        (r'^\[www\.Cpasbien\.com\] ', 'searchre'),
        (r'^\[ www\.Cpasbien\.pw \] ', 'searchre'),
        (r'^\.www\.Cpasbien\.pw', 'searchre'),
        (r'^\[www\.newpct1\.com\]', 'searchre'),
        (r'^\[ www\.Cpasbien\.com \] ', 'searchre'),
        (r'^\{ www\.SceneTime\.com \} - ', 'searchre'),
        (r'^\]\.\[www\.tensiontorrent.com\] - ', 'searchre'),
        (r'^\]\.\[ www\.tensiontorrent.com \] - ', 'searchre'),
        (r'^\[ www\.TorrentDay\.com \] - ', 'searchre'),
        (r'^www\.Torrenting\.com\.-\.', 'searchre'),
        (r'\[rartv\]$', 'searchre'),
        (r'\[rarbg\]$', 'searchre'),
        (r'\.\[eztv\]$', 'searchre'),
        (r'\[eztv\]$', 'searchre'),
        (r'\[ettv\]$', 'searchre'),
        (r'\[cttv\]$', 'searchre'),
        (r'\.\[vtv\]$', 'searchre'),
        (r'\[vtv\]$', 'searchre'),
        (r'\[EtHD\]$', 'searchre'),
        (r'\[GloDLS\]$', 'searchre'),
        (r'\[silv4\]$', 'searchre'),
        (r'\[Seedbox\]$', 'searchre'),
        (r'\[PublicHD\]$', 'searchre'),
        (r'\.\[PublicHD\]$', 'searchre'),
        (r'\.\[NO.RAR\]$', 'searchre'),
        (r'\[NO.RAR\]$', 'searchre'),
        (r'-\=\{SPARROW\}\=-$', 'searchre'),
        (r'\=\{SPARR$', 'searchre'),
        (r'\.\[720P\]\[HEVC\]$', 'searchre'),
        (r'\[AndroidTwoU\]$', 'searchre'),
        (r'\[brassetv\]$', 'searchre'),
        (r'\[Talamasca32\]$', 'searchre'),
        (r'\(musicbolt\.com\)$', 'searchre'),
        (r'\.\(NLsub\)$', 'searchre'),
        (r'\(NLsub\)$', 'searchre'),
        (r'\.\[BT\]$', 'searchre'),
        (r' \[1044\]$', 'searchre'),
        (r'\.RiPSaLoT$', 'searchre'),
        (r'\.GiuseppeTnT$', 'searchre'),
        (r'\.Renc$', 'searchre'),
        (r'\.gz$', 'searchre'),
        (r'\.English$', 'searchre'),
        (r'\.German$', 'searchre'),
        (r'\.\.Italian$', 'searchre'),
        (r'\.Italian$', 'searchre'),
        (r'(?<![57])\.1$', 'searchre'),
        (r'-NZBGEEK$', 'searchre'),
        (r'-Siklopentan$', 'searchre'),
        (r'-Chamele0n$', 'searchre'),
        (r'-Obfuscated$', 'searchre'),
        (r'-BUYMORE$', 'searchre'),
        (r'-\[SpastikusTV\]$', 'searchre'),
        (r'-RP$', 'searchre'),
        (r'-20-40$', 'searchre'),
        (r'\.\[www\.usabit\.com\]$', 'searchre'),
        (r'\[NO-RAR\] - \[ www\.torrentday\.com \]$', 'searchre'),
        (r'- \[ www\.torrentday\.com \]$', 'searchre'),
        (r'- \{ www\.SceneTime\.com \}$', 'searchre'),
        (r'-Scrambled$', 'searchre')
    ])

    _name = name
    for remove_string, remove_type in six.iteritems(removeWordsList):
        if remove_type == 'search':
            _name = _name.replace(remove_string, '')
        elif remove_type == 'searchre':
            _name = re.sub(r'(?i)' + remove_string, '', _name)

    return _name


def replaceExtension(filename, newExt):
    """
    >>> replaceExtension('foo.avi', 'mkv')
    'foo.mkv'
    >>> replaceExtension('.vimrc', 'arglebargle')
    '.vimrc'
    >>> replaceExtension('a.b.c', 'd')
    'a.b.d'
    >>> replaceExtension('', 'a')
    ''
    >>> replaceExtension('foo.bar', '')
    'foo.'
    """
    sepFile = filename.rpartition(".")
    if sepFile[0] == "":
        return filename
    else:
        return sepFile[0] + "." + newExt


def is_torrent_or_nzb_file(filename):
    """
    Check if the provided ``filename`` is a NZB file or a torrent file, based on its extension.
    :param filename: The filename to check
    :return: ``True`` if the ``filename`` is a NZB file or a torrent file, ``False`` otherwise
    """

    if not isinstance(filename, six.string_types):
        return False

    return filename.rpartition('.')[2].lower() in ['nzb', 'torrent']


def is_sync_file(filename):
    """
    Returns true if filename is a syncfile, indicating filesystem may be in flux

    :param filename: Filename to check
    :return: True if this file is a syncfile, False otherwise
    """

    extension = filename.rpartition(".")[2].lower()
    # if extension == '!sync' or extension == 'lftp-pget-status' or extension == 'part' or extension == 'bts':
    syncfiles = sickrage.app.config.sync_files
    if extension in syncfiles.split(",") or filename.startswith('.syncthing'):
        return True
    else:
        return False


def is_media_file(filename):
    """
    Check if named file may contain media

    :param filename: Filename to check
    :return: True if this is a known media file, False if not
    """

    # ignore samples
    if re.search(r'(^|[\W_])(?<!shomin.)(sample\d*)[\W_]', filename, re.I):
        return False

    # ignore RARBG release intro
    if re.search(r'^RARBG\.(\w+\.)?(mp4|avi|txt)$', filename, re.I):
        return False

    # ignore MAC OS's retarded "resource fork" files
    if filename.startswith('._'):
        return False

    sepFile = filename.rpartition(".")

    if re.search('extras?$', sepFile[0], re.I):
        return False

    if sepFile[2].lower() in mediaExtensions:
        return True
    else:
        return False


def is_rar_file(filename):
    """
    Check if file is a RAR file, or part of a RAR set

    :param filename: Filename to check
    :return: True if this is RAR/Part file, False if not
    """

    archive_regex = r'(?P<file>^(?P<base>(?:(?!\.part\d+\.rar$).)*)\.(?:(?:part0*1\.)?rar)$)'
    ret = re.search(archive_regex, filename) is not None
    try:
        if ret and os.path.exists(filename) and os.path.isfile(filename):
            ret = rarfile.is_rarfile(filename)
    except (IOError, OSError):
        pass

    return ret


def sanitizeFileName(name):
    """
    >>> sanitizeFileName('a/b/c')
    'a-b-c'
    >>> sanitizeFileName('abc')
    'abc'
    >>> sanitizeFileName('a"b')
    'ab'
    >>> sanitizeFileName('.a.b..')
    'a.b'
    """

    # remove bad chars from the filename
    name = re.sub(r'[\\/\*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)
    name = re.sub(r'\u2122', '', name)  # Trade Mark Sign

    # remove leading/trailing periods and spaces
    name = name.strip(' .')

    return name


def remove_file_failed(failed_file):
    """
    Remove file from filesystem

    """

    try:
        os.remove(failed_file)
    except Exception:
        pass


def findCertainShow(showList, indexerid):
    """
    Find a show by indexer ID in the show list

    :param showList: List of shows to search in (needle)
    :param indexerid: Show to look for
    :return: result list
    """

    if not indexerid or not showList:
        return None

    indexer_ids = [indexerid] if not isinstance(indexerid, list) else indexerid
    results = [show for show in showList if show.indexerid in indexer_ids]

    if not results:
        return None

    if len(results) == 1:
        return results[0]

    raise MultipleShowObjectsException()


def makeDir(path):
    """
    Make a directory on the filesystem

    :param path: directory to make
    :return: True if success, False if failure
    """

    if not os.path.isdir(path):
        try:
            os.makedirs(path)
            sickrage.app.notifier_providers['synoindex'].addFolder(path)
        except OSError:
            return False
    return True


def list_media_files(path):
    """
    Get a list of files possibly containing media in a path

    :param path: Path to check for files
    :return: list of files
    """

    if not dir or not os.path.isdir(path):
        return []

    files = []
    for curFile in os.listdir(path):
        fullCurFile = os.path.join(path, curFile)

        # if it's a folder do it recursively
        if os.path.isdir(fullCurFile) and not curFile.startswith('.') and not curFile == 'Extras':
            files += list_media_files(fullCurFile)

        elif is_media_file(curFile):
            files.append(fullCurFile)

    return files


def copyFile(srcFile, destFile):
    """
    Copy a file from source to destination

    :param srcFile: Path of source file
    :param destFile: Path of destination file
    """

    try:
        shutil.copyfile(srcFile, destFile)
    except Exception as e:
        sickrage.app.log.warning(e.message)
    else:
        try:
            shutil.copymode(srcFile, destFile)
        except OSError:
            pass


def moveFile(srcFile, destFile):
    """
    Move a file from source to destination

    :param srcFile: Path of source file
    :param destFile: Path of destination file
    """

    try:
        shutil.move(srcFile, destFile)
        fixSetGroupID(destFile)
    except OSError as e:
        copyFile(srcFile, destFile)
        os.unlink(srcFile)


def link(src, dst):
    """
    Create a file link from source to destination.
    TODO: Make this unicode proof

    :param src: Source file
    :param dst: Destination file
    """

    if os.name == 'nt':
        if ctypes.windll.kernel32.CreateHardLinkW(ctypes.c_wchar_p(dst), ctypes.c_wchar_p(src), None) == 0:
            raise ctypes.WinError()
    else:
        os.link(src, dst)


def hardlinkFile(srcFile, destFile):
    """
    Create a hard-link (inside filesystem link) between source and destination

    :param srcFile: Source file
    :param destFile: Destination file
    """

    try:
        link(srcFile, destFile)
        fixSetGroupID(destFile)
    except Exception as e:
        sickrage.app.log.warning("Failed to create hardlink of %s at %s. Error: %r. Copying instead"
                                 % (srcFile, destFile, e))
        copyFile(srcFile, destFile)


def symlink(src, dst):
    """
    Create a soft/symlink between source and destination

    :param src: Source file
    :param dst: Destination file
    """

    if os.name == 'nt':
        if ctypes.windll.kernel32.CreateSymbolicLinkW(ctypes.c_wchar_p(dst), ctypes.c_wchar_p(src),
                                                      1 if os.path.isdir(src) else 0) in [0, 1280]:
            raise ctypes.WinError()
    else:
        os.symlink(src, dst)


def moveAndSymlinkFile(srcFile, destFile):
    """
    Move a file from source to destination, then create a symlink back from destination from source. If this fails, copy
    the file from source to destination

    :param srcFile: Source file
    :param destFile: Destination file
    """

    try:
        shutil.move(srcFile, destFile)
        fixSetGroupID(destFile)
        symlink(destFile, srcFile)
    except Exception as e:
        sickrage.app.log.warning("Failed to create symlink of %s at %s. Error: %r. Copying instead"
                                 % (srcFile, destFile, e))
        copyFile(srcFile, destFile)


def make_dirs(path):
    """
    Creates any folders that are missing and assigns them the permissions of their
    parents
    """

    sickrage.app.log.debug("Checking if the path [{}] already exists".format(path))

    if not os.path.isdir(path):
        # Windows, create all missing folders
        if os.name == 'nt' or os.name == 'ce':
            try:
                sickrage.app.log.debug("Folder %s didn't exist, creating it" % path)
                os.makedirs(path)
            except (OSError, IOError) as e:
                sickrage.app.log.error("Failed creating %s : %r" % (path, e))
                return False

        # not Windows, create all missing folders and set permissions
        else:
            sofar = ''
            folder_list = path.split(os.path.sep)

            # look through each subfolder and make sure they all exist
            for cur_folder in folder_list:
                sofar += cur_folder + os.path.sep

                # if it exists then just keep walking down the line
                if os.path.isdir(sofar):
                    continue

                try:
                    sickrage.app.log.debug("Folder %s didn't exist, creating it" % sofar)
                    os.mkdir(sofar)
                    # use normpath to remove end separator, otherwise checks permissions against itself
                    chmodAsParent(os.path.normpath(sofar))
                    # do the library update for synoindex
                    sickrage.app.notifier_providers['synoindex'].addFolder(sofar)
                except (OSError, IOError) as e:
                    sickrage.app.log.error("Failed creating %s : %r" % (sofar, e))
                    return False

    return True


def delete_empty_folders(check_empty_dir, keep_dir=None):
    """
    Walks backwards up the path and deletes any empty folders found.

    :param check_empty_dir: The path to clean (absolute path to a folder)
    :param keep_dir: Clean until this path is reached
    """

    # treat check_empty_dir as empty when it only contains these items
    ignore_items = []

    sickrage.app.log.info("Trying to clean any empty folders under " + check_empty_dir)

    # as long as the folder exists and doesn't contain any files, delete it
    try:
        while os.path.isdir(check_empty_dir) and check_empty_dir != keep_dir:
            check_files = os.listdir(check_empty_dir)

            if not check_files or (len(check_files) <= len(ignore_items)
                                   and all([check_file in ignore_items for check_file in check_files])):

                try:
                    # directory is empty or contains only ignore_items
                    sickrage.app.log.info("Deleting empty folder: " + check_empty_dir)
                    shutil.rmtree(check_empty_dir)

                    # do the library update for synoindex
                    sickrage.app.notifier_providers['synoindex'].deleteFolder(check_empty_dir)
                except OSError as e:
                    sickrage.app.log.warning("Unable to delete %s. Error: %r" % (check_empty_dir, repr(e)))
                    raise StopIteration
                check_empty_dir = os.path.dirname(check_empty_dir)
            else:
                raise StopIteration
    except StopIteration:
        pass


def fileBitFilter(mode):
    """
    Strip special filesystem bits from file

    :param mode: mode to check and strip
    :return: required mode for media file
    """

    for bit in [stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH, stat.S_ISUID, stat.S_ISGID]:
        if mode & bit:
            mode -= bit

    return mode


def chmodAsParent(childPath):
    """
    Retain permissions of parent for childs
    (Does not work for Windows hosts)

    :param childPath: Child Path to change permissions to sync from parent
    """

    if os.name == 'nt' or os.name == 'ce':
        return

    parentPath = os.path.dirname(childPath)

    if not parentPath:
        sickrage.app.log.debug(
            "No parent path provided in " + childPath + ", unable to get permissions from it")
        return

    childPath = os.path.join(parentPath, os.path.basename(childPath))

    parentPathStat = os.stat(parentPath)
    parentMode = stat.S_IMODE(parentPathStat[stat.ST_MODE])

    childPathStat = os.stat(childPath)
    childPath_mode = stat.S_IMODE(childPathStat[stat.ST_MODE])

    if os.path.isfile(childPath):
        childMode = fileBitFilter(parentMode)
    else:
        childMode = parentMode

    if childPath_mode == childMode:
        return

    childPath_owner = childPathStat.st_uid
    user_id = os.geteuid()  # @UndefinedVariable - only available on UNIX

    if user_id != 0 and user_id != childPath_owner:
        sickrage.app.log.debug(
            "Not running as root or owner of " + childPath + ", not trying to set permissions")
        return

    try:
        os.chmod(childPath, childMode)
        sickrage.app.log.debug(
            "Setting permissions for %s to %o as parent directory has %o" % (childPath, childMode, parentMode))
    except OSError:
        sickrage.app.log.debug("Failed to set permission for %s to %o" % (childPath, childMode))


def fixSetGroupID(childPath):
    """
    Inherid SGID from parent
    (does not work on Windows hosts)

    :param childPath: Path to inherit SGID permissions from parent
    """

    if os.name == 'nt' or os.name == 'ce':
        return

    parentPath = os.path.dirname(childPath)
    parentStat = os.stat(parentPath)
    parentMode = stat.S_IMODE(parentStat[stat.ST_MODE])

    childPath = os.path.join(parentPath, os.path.basename(childPath))

    if parentMode & stat.S_ISGID:
        parentGID = parentStat[stat.ST_GID]
        childStat = os.stat(childPath)
        childGID = childStat[stat.ST_GID]

        if childGID == parentGID:
            return

        childPath_owner = childStat.st_uid
        user_id = os.geteuid()  # @UndefinedVariable - only available on UNIX

        if user_id != 0 and user_id != childPath_owner:
            sickrage.app.log.debug(
                "Not running as root or owner of " + childPath + ", not trying to set the set-group-ID")
            return

        try:
            os.chown(childPath, -1, parentGID)  # @UndefinedVariable - only available on UNIX
            sickrage.app.log.debug("Respecting the set-group-ID bit on the parent directory for %s" % childPath)
        except OSError:
            sickrage.app.log.error(
                "Failed to respect the set-group-ID bit on the parent directory for %s (setting group ID %i)" % (
                    childPath, parentGID))


def sanitizeSceneName(name, anime=False):
    """
    Takes a show name and returns the "scenified" version of it.

    :param anime: Some show have a ' in their name(Kuroko's Basketball) and is needed for search.
    :return: A string containing the scene version of the show name given.
    """

    if not name:
        return ''

    bad_chars = ',:()!?\u2019'
    if not anime:
        bad_chars += "'"

    # strip out any bad chars
    for x in bad_chars:
        name = name.replace(x, "")

    # tidy up stuff that doesn't belong in scene names
    name = name.replace("- ", ".").replace(" ", ".").replace("&", "and").replace('/', '.')
    name = re.sub(r"\.\.*", ".", name)

    if name.endswith('.'):
        name = name[:-1]

    return name


def create_https_certificates(ssl_cert, ssl_key):
    """This function takes a domain name as a parameter and then creates a certificate and key with the
    domain name(replacing dots by underscores), finally signing the certificate using specified CA and
    returns the path of key and cert files. If you are yet to generate a CA then check the top comments"""

    try:
        import OpenSSL
    except ImportError:
        sickrage.app.log.error(
            "OpenSSL not available, please install for better requests validation: `https://pyopenssl.readthedocs.org/en/latest/install.html`")
        return False

    # Check happens if the certificate and key pair already exists for a domain
    if not os.path.exists(ssl_key) and os.path.exists(ssl_cert):
        # Serial Generation - Serial number must be unique for each certificate,
        serial = int(time.time())

        # Create the CA Certificate
        cakey = OpenSSL.crypto.PKey().generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
        careq = OpenSSL.crypto.X509()
        careq.get_subject().CN = "Certificate Authority"
        careq.set_pubkey(cakey)
        careq.sign(cakey, "sha1")

        # Sign the CA Certificate
        cacert = OpenSSL.crypto.X509()
        cacert.set_serial_number(serial)
        cacert.gmtime_adj_notBefore(0)
        cacert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cacert.set_issuer(careq.get_subject())
        cacert.set_subject(careq.get_subject())
        cacert.set_pubkey(careq.get_pubkey())
        cacert.sign(cakey, "sha1")

        # Generate self-signed certificate
        key = OpenSSL.crypto.PKey()
        key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
        cert = OpenSSL.crypto.X509()
        cert.get_subject().CN = "SiCKRAGE"
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cert.set_serial_number(serial)
        cert.set_issuer(cacert.get_subject())
        cert.set_pubkey(key)
        cert.sign(cakey, "sha1")

        # Save the key and certificate to disk
        try:
            # pylint: disable=E1101
            # Module has no member
            with io.open(ssl_key, 'w') as keyout:
                keyout.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
            with io.open(ssl_cert, 'w') as certout:
                certout.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
        except Exception:
            sickrage.app.log.error("Error creating SSL key and certificate")
            return False

    return True


def get_lan_ip():
    """Return IP of system."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    return s.getsockname()[0]


def anon_url(*url):
    """
    Return a URL string consisting of the Anonymous redirect URL and an arbitrary number of values appended.
    """

    url = ''.join(map(unicode, url))

    # Handle URL's containing https or http, previously only handled http
    uri_pattern = ur'^https?://'
    unicode_uri_pattern = re.compile(uri_pattern, re.UNICODE)
    if not re.search(unicode_uri_pattern, url):
        url = 'http://' + url

    return '{}{}'.format(sickrage.app.config.anon_redirect, url)


def full_sanitizeSceneName(name):
    return re.sub('[. -]', ' ', sanitizeSceneName(name)).lower().lstrip()


def is_hidden_folder(folder):
    """
    Returns True if folder is hidden.
    On Linux based systems hidden folders start with . (dot)
    :param folder: Full path of folder to check
    """

    def is_hidden(filepath):
        name = os.path.basename(os.path.abspath(filepath))
        return name.startswith('.') or has_hidden_attribute(filepath)

    def has_hidden_attribute(filepath):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            result = False
        return result

    if os.path.isdir(folder):
        if is_hidden(folder):
            return True

    return False


def real_path(path):
    """
    Returns: the canonicalized absolute pathname. The resulting path will have no symbolic link, '/./' or '/../' components.
    """
    return os.path.normpath(os.path.normcase(os.path.realpath(path)))


def extract_zipfile(archive, targetDir):
    """
    Unzip a file to a directory

    :param archive: The file name for the archive with a full path
    """

    try:
        if not os.path.exists(targetDir):
            os.mkdir(targetDir)

        zip_file = zipfile.ZipFile(archive, 'r', allowZip64=True)
        for member in zip_file.namelist():
            filename = os.path.basename(member)
            # skip directories
            if not filename:
                continue

            # copy file (taken from zipfile's extract)
            source = zip_file.open(member)
            target = io.open(os.path.join(targetDir, filename), "wb")
            shutil.copyfileobj(source, target)
            source.close()
            target.close()
        zip_file.close()
        return True
    except Exception as e:
        sickrage.app.log.error("Zip extraction error: %r " % repr(e))
        return False


def create_zipfile(fileList, archive, arcname=None):
    """
    Store the config file as a ZIP

    :param fileList: List of files to store
    :param archive: ZIP file name
    :param arcname: Archive path
    :return: True on success, False on failure
    """

    try:
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            for f in list(set(fileList)):
                z.write(f, os.path.relpath(f, arcname))
        return True
    except Exception as e:
        sickrage.app.log.error("Zip creation error: {} ".format(e.message))
        return False


def restoreConfigZip(archive, targetDir, restore_database=True, restore_config=True, restore_cache=True):
    """
    Restores a backup ZIP file back in place

    :param archive: ZIP filename
    :param targetDir: Directory to restore to
    :return: True on success, False on failure
    """

    try:
        if not os.path.exists(targetDir):
            os.mkdir(targetDir)
        else:
            def path_leaf(path):
                head, tail = os.path.split(path)
                return tail or os.path.basename(head)

            bakFilename = '{0}-{1}'.format(path_leaf(targetDir), datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            moveFile(targetDir, os.path.join(os.path.dirname(targetDir), bakFilename))

        with zipfile.ZipFile(archive, 'r', allowZip64=True) as zip_file:
            for member in zip_file.namelist():
                if not restore_database and member.split('/')[0] == 'database':
                    continue

                if not restore_config and member.split('/')[0] == 'config.ini':
                    continue

                if not restore_cache and member.split('/')[0] == 'cache':
                    continue

                zip_file.extract(member, targetDir)

        return True
    except Exception as e:
        sickrage.app.log.error("Zip extraction error: {}".format(e.message))
        shutil.rmtree(targetDir)


def backupSR(backupDir, keep_latest=False):
    source = []

    filesList = ['sickrage.db',
                 'failed.db',
                 'cache.db',
                 os.path.basename(sickrage.app.config_file)]

    def _keep_latest_backup():
        import glob

        for f in sorted(glob.glob(os.path.join(backupDir, '*.zip')), key=os.path.getctime, reverse=True)[1:]:
            os.remove(f)

    if keep_latest:
        _keep_latest_backup()

    # individual files
    for f in filesList:
        fp = os.path.join(sickrage.app.data_dir, f)
        if os.path.exists(fp):
            source += [fp]

    # database folder
    for (path, __, files) in os.walk(os.path.join(sickrage.app.data_dir, 'database'), topdown=True):
        for filename in files:
            source += [os.path.join(path, filename)]

    # cache folder
    if sickrage.app.cache_dir:
        for (path, dirs, files) in os.walk(sickrage.app.cache_dir, topdown=True):
            for dirname in dirs:
                if path == sickrage.app.cache_dir and dirname not in ['images']:
                    dirs.remove(dirname)

            for filename in files:
                source += [os.path.join(path, filename)]

    # ZIP filename
    target = os.path.join(backupDir, 'sickrage-{}.zip'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S')))

    return create_zipfile(source, target, sickrage.app.data_dir)


def restoreSR(srcDir, dstDir):
    try:
        filesList = ['sickrage.db',
                     'sickbeard.db',
                     'failed.db',
                     'cache.db',
                     os.path.basename(sickrage.app.config_file)]

        for filename in filesList:
            srcFile = os.path.join(srcDir, filename)
            dstFile = os.path.join(dstDir, filename)
            bakFile = os.path.join(dstDir, '{}.bak-{}'
                                   .format(filename, datetime.datetime.now().strftime('%Y%m%d_%H%M%S')))

            if os.path.exists(srcFile):
                if os.path.isfile(dstFile):
                    moveFile(dstFile, bakFile)
                moveFile(srcFile, dstFile)

        # databse
        if os.path.exists(os.path.join(srcDir, 'database')):
            if os.path.exists(os.path.join(dstDir, 'database')):
                moveFile(os.path.join(dstDir, 'database'), os.path.join(dstDir, '{}.bak-{}'
                                                                        .format('database',
                                                                                datetime.datetime.now().strftime(
                                                                                    '%Y%m%d_%H%M%S'))))
            moveFile(os.path.join(srcDir, 'database'), dstDir)

        # cache
        if os.path.exists(os.path.join(srcDir, 'cache')):
            if os.path.exists(os.path.join(dstDir, 'cache')):
                moveFile(os.path.join(dstDir, 'cache'), os.path.join(dstDir, '{}.bak-{}'
                                                                     .format('cache',
                                                                             datetime.datetime.now().strftime(
                                                                                 '%Y%m%d_%H%M%S'))))
            moveFile(os.path.join(srcDir, 'cache'), dstDir)

        return True
    except Exception as e:
        return False


def touchFile(fname, atime=None):
    """
    Touch a file (change modification date)

    :param fname: Filename to touch
    :param atime: Specific access time (defaults to None)
    :return: True on success, False on failure
    """

    if atime and fname and os.path.isfile(fname):
        os.utime(fname, (atime, atime))
        return True

    return False


def get_size(start_path='.'):
    """
    Find the total dir and filesize of a path

    :param start_path: Path to recursively count size
    :return: total filesize
    """

    if not os.path.isdir(start_path):
        return -1

    total_size = 0

    try:
        for dirpath, __, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError as e:
                    sickrage.app.log.error("Unable to get size for file %s Error: %r" % (fp, e))
                    sickrage.app.log.debug(traceback.format_exc())
    except Exception as e:
        pass

    return total_size


def generateApiKey():
    """ Return a new randomized API_KEY"""

    try:
        from hashlib import md5
    except ImportError:
        from md5 import md5

    # Create some values to seed md5
    t = str(time.time())
    r = str(random.random())

    # Create the md5 instance and give it the current time
    m = md5(t)

    # Update the md5 instance with the random variable
    m.update(r)

    # Return a hex digest of the md5, eg 49f68a5c8493ec2c0bf489821c21fc3b
    sickrage.app.log.debug("New API key generated")
    return m.hexdigest()


def pretty_filesize(file_bytes):
    """Return humanly formatted sizes from bytes"""
    for mod in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if file_bytes < 1024.00:
            return "%3.2f %s" % (file_bytes, mod)
        file_bytes /= 1024.00


def remove_article(text=''):
    """Remove the english articles from a text string"""

    return re.sub(r'(?i)^(?:(?:A(?!\s+to)n?)|The)\s(\w)', r'\1', text)


def generateCookieSecret():
    """Generate a new cookie secret"""

    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)


def verify_freespace(src, dest, oldfile=None):
    """
    Checks if the target system has enough free space to copy or move a file.

    :param src: Source filename
    :param dest: Destination path
    :param oldfile: File to be replaced (defaults to None)
    :return: True if there is enough space for the file, False if there isn't. Also returns True if the OS doesn't support this option
    """

    if not isinstance(oldfile, list):
        oldfile = [oldfile]

    sickrage.app.log.debug("Trying to determine free space on destination drive")

    if hasattr(os, 'statvfs'):  # POSIX
        def disk_usage(path):
            st = os.statvfs(path)
            free = st.f_bavail * st.f_frsize
            return free

    elif os.name == 'nt':  # Windows
        import sys

        def disk_usage(path):
            __, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
            if sys.version_info >= (3,) or isinstance(path, unicode):
                fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
            else:
                fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA
            ret = fun(path, ctypes.byref(__), ctypes.byref(total), ctypes.byref(free))
            if ret == 0:
                sickrage.app.log.warning("Unable to determine free space, something went wrong")
                raise ctypes.WinError()
            return free.value
    else:
        sickrage.app.log.info("Unable to determine free space on your OS")
        return True

    if not os.path.isfile(src):
        sickrage.app.log.warning("A path to a file is required for the source. " + src + " is not a file.")
        return True

    try:
        diskfree = disk_usage(dest)
    except Exception:
        sickrage.app.log.warning("Unable to determine free space, so I will assume there is enough.")
        return True

    neededspace = int(os.path.getsize(src))

    if oldfile:
        for f in oldfile:
            if os.path.isfile(f.location):
                diskfree += os.path.getsize(f.location)

    if diskfree > neededspace:
        return True
    else:
        sickrage.app.log.warning("Not enough free space: Needed: %s bytes ( %s ), found: %s bytes ( %s )"
                                 % (neededspace, pretty_filesize(neededspace), diskfree,
                                    pretty_filesize(diskfree)))
        return False


def pretty_time_delta(seconds):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    time_delta = sign_string

    if days > 0:
        time_delta += ' %dd' % days
    if hours > 0:
        time_delta += ' %dh' % hours
    if minutes > 0:
        time_delta += ' %dm' % minutes
    if seconds > 0:
        time_delta += ' %ds' % seconds

    return time_delta


def isFileLocked(checkfile, writeLockCheck=False):
    """
    Checks to see if a file is locked. Performs three checks
        1. Checks if the file even exists
        2. Attempts to open the file for reading. This will determine if the file has a write lock.
            Write locks occur when the file is being edited or copied to, e.g. a file copy destination
        3. If the readLockCheck parameter is True, attempts to rename the file. If this fails the
            file is open by some other process for reading. The file can be read, but not written to
            or deleted.
    :param checkfile: the file being checked
    :param writeLockCheck: when true will check if the file is locked for writing (prevents move operations)
    """

    checkfile = os.path.abspath(checkfile)

    if not os.path.exists(checkfile):
        return True
    try:
        with io.open(checkfile, 'rb'):
            pass
    except IOError:
        return True

    if writeLockCheck:
        lockFile = checkfile + ".lckchk"
        if os.path.exists(lockFile):
            os.remove(lockFile)

        try:
            os.rename(checkfile, lockFile)
            time.sleep(1)
            os.rename(lockFile, checkfile)
        except (OSError, IOError):
            return True

    return False


def getDiskSpaceUsage(diskPath=None):
    """
    returns the free space in human readable bytes for a given path or False if no path given
    :param diskPath: the filesystem path being checked
    """
    if diskPath and os.path.exists(diskPath):
        if platform.system() == 'Windows':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(diskPath), None, None,
                                                       ctypes.pointer(free_bytes))
            return pretty_filesize(free_bytes.value)
        else:
            st = os.statvfs(diskPath)
            return pretty_filesize(st.f_bavail * st.f_frsize)
    else:
        return False


def getFreeSpace(directories):
    single = not isinstance(directories, (tuple, list))
    if single:
        directories = [directories]

    free_space = {}
    for folder in directories:

        size = None
        if os.path.isdir(folder):
            if os.name == 'nt':
                __, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()

                if sys.version_info >= (3,) or isinstance(folder, unicode):
                    fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
                else:
                    fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA

                ret = fun(folder, ctypes.byref(__), ctypes.byref(total), ctypes.byref(free))
                if ret == 0: raise ctypes.WinError()

                return [total.value, free.value]
            else:
                s = os.statvfs(folder)

                size = [s.f_blocks * s.f_frsize / (1024 * 1024), (s.f_bavail * s.f_frsize) / (1024 * 1024)]

        if single: return size

        free_space[folder] = size

    return free_space


def restoreVersionedFile(backup_file, version):
    """
    Restore a file version to original state

    :param backup_file: File to restore
    :param version: Version of file to restore
    :return: True on success, False on failure
    """

    numTries = 0

    new_file, __ = os.path.splitext(backup_file)
    restore_file = '{}.v{}'.format(new_file, version)

    if not os.path.isfile(new_file):
        sickrage.app.log.debug("Not restoring, %s doesn't exist" % new_file)
        return False

    try:
        sickrage.app.log.debug("Trying to backup %s to %s.r%s before restoring backup"
                               % (new_file, new_file, version))

        moveFile(new_file, new_file + '.' + 'r' + str(version))
    except Exception as e:
        sickrage.app.log.warning("Error while trying to backup file %s before proceeding with restore: %r"
                                 % (restore_file, e))
        return False

    while not os.path.isfile(new_file):
        if not os.path.isfile(restore_file):
            sickrage.app.log.debug("Not restoring, %s doesn't exist" % restore_file)
            break

        try:
            sickrage.app.log.debug("Trying to restore file %s to %s" % (restore_file, new_file))
            shutil.copy(restore_file, new_file)
            sickrage.app.log.debug("Restore done")
            break
        except Exception as e:
            sickrage.app.log.warning("Error while trying to restore file %s. Error: %r" % (restore_file, e))
            numTries += 1
            time.sleep(1)
            sickrage.app.log.debug("Trying again. Attempt #: %s" % numTries)

        if numTries >= 10:
            sickrage.app.log.warning("Unable to restore file %s to %s" % (restore_file, new_file))
            return False

    return True


def backupVersionedFile(old_file, version):
    """
    Back up an old version of a file

    :param old_file: Original file, to take a backup from
    :param version: Version of file to store in backup
    :return: True if success, False if failure
    """

    numTries = 0

    new_file = '{}.v{}'.format(old_file, version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            sickrage.app.log.debug("Not creating backup, %s doesn't exist" % old_file)
            break

        try:
            sickrage.app.log.debug("Trying to back up %s to %s" % (old_file, new_file))
            shutil.copyfile(old_file, new_file)
            sickrage.app.log.debug("Backup done")
            break
        except Exception as e:
            sickrage.app.log.warning("Error while trying to back up %s to %s : %r" % (old_file, new_file, e))
            numTries += 1
            time.sleep(1)
            sickrage.app.log.debug("Trying again.")

        if numTries >= 10:
            sickrage.app.log.error("Unable to back up %s to %s please do it manually." % (old_file, new_file))
            return False

    return True


@contextmanager
def bs4_parser(markup, features="html5lib", *args, **kwargs):
    try:
        _soup = BeautifulSoup(markup, features=features, *args, **kwargs)
    except:
        _soup = BeautifulSoup(markup, features="html.parser", *args, **kwargs)

    try:
        yield _soup
    finally:
        _soup.clear(True)


def getFileSize(file):
    try:
        return os.path.getsize(file) / 1024 / 1024
    except:
        return None


def get_temp_dir():
    """
    Returns the [system temp dir]/sickrage-u501 or sickrage-myuser
    """

    import getpass

    if hasattr(os, 'getuid'):
        uid = "u%d" % (os.getuid())
    else:
        # For Windows
        try:
            uid = getpass.getuser()
        except ImportError:
            return os.path.join(tempfile.gettempdir(), "sickrage")

    return os.path.join(tempfile.gettempdir(), "sickrage-%s" % uid)


def scrub(obj):
    if isinstance(obj, dict):
        for k in obj.keys():
            scrub(obj[k])
            del obj[k]
    elif isinstance(obj, list):
        for i in reversed(range(len(obj))):
            scrub(obj[i])
            del obj[i]


def convert_size(size, default=0, units=None):
    if units is None:
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    size_regex = re.compile(r'([\d+.]+)\s?({})?'.format('|'.join(units)), re.I)

    try:
        size, unit = float(size_regex.search(str(size)).group(1) or -1), size_regex.search(str(size)).group(2) or 'B'
    except Exception:
        return default

    size *= 1024 ** units.index(unit.upper())

    return max(long(size), 0)


def randomString(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def clean_url(url):
    """
    Returns an cleaned url starting with a scheme and folder with trailing /
    or an empty string
    """

    urlparse.uses_netloc.append('scgi')

    if url and url.strip():

        url = url.strip()

        if '://' not in url:
            url = '//' + url

        scheme, netloc, path, query, fragment = urlparse.urlsplit(url, 'http')

        if not path:
            path += '/'

        cleaned_url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    else:
        cleaned_url = ''

    return cleaned_url


def overall_stats():
    shows = sickrage.app.showlist
    today = str(datetime.date.today().toordinal())

    downloaded_status = Quality.DOWNLOADED + Quality.ARCHIVED
    snatched_status = Quality.SNATCHED + Quality.SNATCHED_PROPER
    total_status = [SKIPPED, WANTED]

    stats = {
        'episodes': {
            'downloaded': 0,
            'snatched': 0,
            'total': 0,
        },
        'shows': {
            'active': len([show for show in shows if show.paused == 0 and show.status.lower() == 'continuing']),
            'total': len(shows),
        },
        'total_size': 0
    }

    for result in [x['doc'] for x in sickrage.app.main_db.db.all('tv_episodes', with_doc=True)]:
        if not (result['season'] > 0 and result['episode'] > 0 and result['airdate'] > 1):
            continue

        if result['status'] in downloaded_status:
            stats['episodes']['downloaded'] += 1
            stats['episodes']['total'] += 1
        elif result['status'] in snatched_status:
            stats['episodes']['snatched'] += 1
            stats['episodes']['total'] += 1
        elif result['airdate'] <= today and result['status'] in total_status:
            stats['episodes']['total'] += 1

        stats['total_size'] += result['file_size']

    return stats


def launch_browser(protocol=None, host=None, startport=None):
    browserurl = '{}://{}:{}/home/'.format(protocol or 'http', host, startport or 8081)

    try:
        sickrage.app.log.info("Launching browser window")

        try:
            webbrowser.open(browserurl, 2, 1)
        except webbrowser.Error:
            webbrowser.open(browserurl, 1, 1)
    except webbrowser.Error:
        print("Unable to launch a browser")


def is_ip_private(ip):
    priv_lo = re.compile(r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    priv_24 = re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    priv_20 = re.compile(r"^192\.168\.\d{1,3}.\d{1,3}$")
    priv_16 = re.compile(r"^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$")
    return priv_lo.match(ip) or priv_24.match(ip) or priv_20.match(ip) or priv_16.match(ip)


def validate_url(value):
    """
    Return whether or not given value is a valid URL.
    :param value: URL address string to validate
    """

    regex = (
        r'^[a-z]+://([^/:]+{tld}|([0-9]{{1,3}}\.)'
        r'{{3}}[0-9]{{1,3}})(:[0-9]+)?(\/.*)?$'
    )

    return (True, False)[not re.compile(regex.format(tld=r'\.[a-z]{2,10}')).match(value)]


def torrent_webui_url():
    if not sickrage.app.config.use_torrents or \
            not sickrage.app.config.torrent_host.lower().startswith('http') or \
                    sickrage.app.config.torrent_method == 'blackhole' or sickrage.app.config.enable_https and \
            not sickrage.app.config.torrent_host.lower().startswith('https'):
        return ''

    torrent_ui_url = re.sub('localhost|127.0.0.1', sickrage.app.config.web_host or get_lan_ip(),
                            sickrage.app.config.torrent_host or '', re.I)

    def test_exists(url):
        try:
            h = requests.head(url)
            return h.status_code != 404
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            return False

    if sickrage.app.config.torrent_method == 'utorrent':
        torrent_ui_url = '/'.join(s.strip('/') for s in (torrent_ui_url, 'gui/'))
    elif sickrage.app.config.torrent_method == 'download_station':
        if test_exists(urlparse.urljoin(torrent_ui_url, 'download/')):
            torrent_ui_url = urlparse.urljoin(torrent_ui_url, 'download/')

    return ('', torrent_ui_url)[test_exists(torrent_ui_url)]


def checkbox_to_value(option, value_on=True, value_off=False):
    """
    Turns checkbox option 'on' or 'true' to value_on (1)
    any other value returns value_off (0)
    """

    if isinstance(option, list):
        option = option[-1]
    if isinstance(option, six.string_types):
        option = six.text_type(option).strip().lower()

    if option in (True, 'on', 'true', value_on) or try_int(option) > 0:
        return value_on

    return value_off


def clean_host(host, default_port=None):
    """
    Returns host or host:port or empty string from a given url or host
    If no port is found and default_port is given use host:default_port
    """

    host = host.strip()

    if host:

        match_host_port = re.search(r'(?:http.*://)?(?P<host>[^:/]+).?(?P<port>[0-9]*).*', host)

        cleaned_host = match_host_port.group('host')
        cleaned_port = match_host_port.group('port')

        if cleaned_host:

            if cleaned_port:
                host = cleaned_host + ':' + cleaned_port

            elif default_port:
                host = cleaned_host + ':' + str(default_port)

            else:
                host = cleaned_host

        else:
            host = ''

    return host


def clean_hosts(hosts, default_port=None):
    """
    Returns list of cleaned hosts by Config.clean_host

    :param hosts: list of hosts
    :param default_port: default port to use
    :return: list of cleaned hosts
    """
    cleaned_hosts = []

    for cur_host in [x.strip() for x in hosts.split(",")]:
        if cur_host:
            cleaned_host = clean_host(cur_host, default_port)
            if cleaned_host:
                cleaned_hosts.append(cleaned_host)

    if cleaned_hosts:
        cleaned_hosts = ",".join(cleaned_hosts)

    else:
        cleaned_hosts = ''

    return cleaned_hosts


def glob_escape(pathname):
    """
    Escape all special characters.
    """

    MAGIC_CHECK = re.compile(r'([*?[])')
    MAGIC_CHECK_BYTES = re.compile(r'([*?[])')

    drive, pathname = os.path.splitdrive(pathname)
    if isinstance(pathname, bytes):
        pathname = MAGIC_CHECK_BYTES.sub(r'[\1]', pathname)
    else:
        pathname = MAGIC_CHECK.sub(r'[\1]', pathname)

    return drive + pathname
