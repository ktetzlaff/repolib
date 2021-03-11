#! /usr/bin/python3

"""
repolib PPA Signing Key Support

From software-properties

Copyright (c) 2004-2009 Canonical Ltd.
          (c) 2019-2020 Ian Santopietro <isantop@gmail.com>

Author: Michael Vogt <mvo@debian.org>
        Ian Santopietro <isantop@gmail.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
"""
#pylint: disable=too-many-ancestors
# If we want to use the subclass, we don't have a lot of options.

from __future__ import print_function

import subprocess
import tempfile
from pathlib import Path

import dbus

# Allow failing (and don't fetch from LP if we did)
try:
    from launchpadlib.launchpad import Launchpad
    from lazr.restfulclient.errors import BadRequest, NotFound, Unauthorized
except ImportError:
    Launchpad = None

from . import source, util

DISTRO_CODENAME = util.DISTRO_CODENAME

SKS_KEYSERVER = 'https://keyserver.ubuntu.com/pks/lookup?op=get&options=mr&exact=on&search=0x%s'
# maintained until 2015
LAUNCHPAD_PPA_API = 'https://launchpad.net/api/devel/%s/+archive/%s'
LAUNCHPAD_USER_API = 'https://launchpad.net/api/1.0/%s'
LAUNCHPAD_USER_PPAS_API = 'https://launchpad.net/api/1.0/%s/ppas'
LAUNCHPAD_DISTRIBUTION_API = 'https://launchpad.net/api/1.0/%s'
LAUNCHPAD_DISTRIBUTION_SERIES_API = 'https://launchpad.net/api/1.0/%s/%s'
# Specify to use the system default SSL store; change to a different path
# to test with custom certificates.
LAUNCHPAD_PPA_CERT = "/etc/ssl/certs/ca-certificates.crt"

GPG_KEYBOX_CMD = [
    'gpg',
    '-q',
    '--no-options',
    '--no-default-keyring',
    '--batch'
]

GPG_KEYRING_CMD = [
    'gpg',
    '-q',
    '--no-options',
    '--no-default-keyring'
]

class PPAError(Exception):
    """ Exception from a PPA or PPALine object.

    Portions of this class have been adapted from SoftwareProperties. For
    """

    def __init__(self, *args, code=1, **kwargs):
        """Exception with a PPA or PPALine object

        Arguments:
            code (:obj:`int`, optional, default=1): Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code = code

class PPA:
    """ An object to fetch data from PPAs. """

    def __init__(self, teamname, ppaname):
        self.teamname = teamname
        self.ppaname = ppaname
        self._lap = None
        self._lpteam = None
        self._lpppa = None
        self._signing_key_data = None
        self._fingerprint = None

    @property
    def lap(self):
        """ The Launchpad Object."""
        if not self._lap:
            self._lap = Launchpad.login_anonymously(
                f'{self.__module__}.{self.__class__.__name__}',
                service_root='production',
                version='devel'
            )
        return self._lap

    @property
    def lpteam(self):
        """ The Launchpad object for the PPA's owner."""
        if not self._lpteam:
            try:
                self._lpteam = self.lap.people(self.teamname)
            except NotFound as err:
                msg = f'User/Team "{self.teamname}" not found'
                raise PPAError(msg) from err
            except Unauthorized as err:
                msg = f'Invalid user/team name "{self.teamname}"'
                raise PPAError(msg) from err
        return self._lpteam

    @property
    def lpppa(self):
        """ The Launchpad object for the PPA."""
        if not self._lpppa:
            try:
                self._lpppa = self.lpteam.getPPAByName(name=self.ppaname)
            except NotFound as err:
                msg = f'PPA "{self.teamname}/{self.ppaname}"" not found'
                raise PPAError(msg) from err
            except BadRequest as err:
                msg = f'Invalid PPA name "{self.ppaname}"'
                raise PPAError(msg) from err
        return self._lpppa

    @property
    def description(self):
        """str: The description of the PPA."""
        return self.lpppa.description

    @property
    def displayname(self):
        """ str: the fancy name of the PPA."""
        return self.lpppa.displayname

    @property
    def fingerprint(self):
        """ str: the fingerprint of the signing key."""
        if not self._fingerprint:
            self._fingerprint = self.lpppa.signing_key_fingerprint
        return self._fingerprint

    @property
    def trustedparts_content(self):
        """ str: The contents of the key file."""
        if not self._signing_key_data:
            key = self.lpppa.getSigningKeyData()
            fingerprint = self.fingerprint

            if not fingerprint:
                print("Warning: could not get PPA signing_key_fingerprint from LP, using anyway")
            elif 'redacted' in fingerprint:
                print("Private PPA fingerprint redacted, using key anyway (LP: #1879781)")

            self._signing_key_data = key
        return self._signing_key_data


class PPASource(source.Source):
    """ PPA Source shortcut

    These are given in the format ppa:owner/name. Much of this code is adapted 
    from SoftwareProperties.

    Arguments:
        shortcut (str): The ppa: shortcut to process
        fetch_data (bool): Whether to try and fetch metadata from Launchpad.
    """

    def __init__(self, shortcut, fetch_data=True, verbose=False):
        if not shortcut.startswith('ppa:'):
            raise PPAError(f'The PPA shortcut {shortcut} is malformed')
        super().__init__()
        self.shortcut = shortcut
        self.verbose = verbose
        self.ppa = None
    
    def load_from_shortcut(self, fetch_data=True):
        """ Fills in the attributes based on the Shortcut details.

        Arguments:
            fetch_data (bool): Whether to fetch metadata from Launchpad.
        """
        self.init_values()

        self.raw_ppa = self.shortcut.replace('ppa:', '').split('/')
        ppa_owner = self.raw_ppa[0]
        ppa_name = self.raw_ppa[1]
        
        self.ident = f'ppa-{ppa_owner}-{ppa_name}'
        self.name = self.make_default_name()
        self.uris = [f'http://ppa.launchpad.net/{ppa_owner}/{ppa_name}/ubuntu']
        self.suites = [DISTRO_CODENAME]
        self.components = ['main']

        if fetch_data:
            self.ppa = get_info_from_lp(ppa_owner, ppa_name)

        self.enabled = True
    
    def copy(self, source_code=False):
        """Copies the source and returns an identical source object.

        Arguments:
            source_code (bool): if True, output an identical source, except with
                source code enabled.

        Returns:
            A Source() object identical to self.
        """
        new_source = PPASource(self.shortcut)
        new_source = super().copy(source_code=source_code)
        if self.ppa:
            new_source.ppa = self.ppa
        return new_source

    def make_default_name(self, prefix='ppa-'):
        """ Create a name which works for a PPA."""
        name = f'{prefix}{self.raw_ppa[0]}-{self.raw_ppa[1]}'
        return name
    
    def make_key(self, debug=False, log=None):
        """ Add a signing key from launchpad.

        Note: this method will fail if there isn't any PPA object for this
        source.
        """
        key_path = util.get_keys_dir() / f'{self.ident}.gpg'
        import_dest = Path('/tmp', key_path.name)
        if debug:
            if log:
                log.info(
                    'Would fetch key with fingerprint %s to %s',
                    self.ppa.fingerprint,
                    key_path
                )
            return
        
        if not self.ppa:
            raise PPAError('Have not fetched PPA Metadata')
        key_data = self.ppa.trustedparts_content

        if not key_data:
            if log:
                log.warning(
                    ('Could not fetch key %s from keyserver. Check your '
                     'internet connection. Re-run this command to try again'),
                    self.ppa.fingerprint
                )
            return
        
        with tempfile.TemporaryDirectory as tempdir:
            import_cmd = GPG_KEYBOX_CMD.copy()
            import_cmd += [
                f'--keyring={import_dest}', '--homedir', tempdir, '--import'
            ]
            export_cmd = GPG_KEYRING_CMD.copy()
            export_cmd += [f'--keyring={import_dest}', '--export']

            try:
                with open(key_path, mode='wb') as key_file:
                    subprocess.run(import_cmd, check=True, input=key_data.encode())
                    subprocess.run(export_cmd, check=True, stdout=key_file)
            except PermissionError:
                subprocess.run(import_cmd, check=True, input=key_data.encode())
                bus = dbus.SystemBus()
                privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
                export_cmd += [str(key_path)]
                privileged_object.add_apt_signing_key(export_cmd)


def get_info_from_lp(owner_name, ppa):
    """ Attempt to get information on a PPA from launchpad over the internet.

    Arguments:
        owner_name (str): The Launchpad user owning the PPA.
        ppa (str): The name of the PPA

    Returns:
        json: The PPA information as a JSON object.
    """
    ppa = PPA(owner_name, ppa)
    return ppa
