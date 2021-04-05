#!/usr/bin/python3

"""
Copyright (c) 2019-2020, Ian Santopietro
All rights reserved.

This file is part of RepoLib.

RepoLib is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RepoLib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RepoLib.  If not, see <https://www.gnu.org/licenses/>.
"""

from .source import Source
from .system import SystemSource
from .legacy_deb import LegacyDebSource
from .file import SourceFile
from .deb import DebLine
from .ppa import PPASource
from .util import AptSourceEnabled, AptSourceType, RepoError
from . import util
from . import ppa
from . import __version__

VERSION = __version__.__version__

# pylint: disable=broad-except
# We want to be broad in catching exceptions here, as failure could mean
# applications unexpectedly close
def get_all_sources(get_system=False):
    """ Returns a list of all the sources on the system.

    Arguments:
        get_system (bool): Whether to include the system repository or not.

    Returns:
        Without `get_exceptions`, return the :obj:`list` of :obj:`Source`
        With `get_exceptions`, return: (
            :obj:`list` of :obj:`Source`,
            :obj:`dict` of :obj:`Exception`
        )
    """
    files, errors = get_all_files(get_system=get_system)

    sources = []

    for file in files:
        for source in file.sources.values():
            has_uris = len(source.uris) > 0
            has_suites = len(source.suites) > 0
            if has_uris and has_suites:
                sources.append(source)

    return sources, errors

def get_all_files(get_system=False):
    """ Returns a list of all the source files on the system.

    Arguments:
        get_system (bool): Whether to include the system repository or not.

    Returns:
        Without `get_exceptions`, return the :obj:`list` of :obj:`Source`
        With `get_exceptions`, return: (
            :obj:`list` of :obj:`SourceFile`,
            :obj:`dict` of :obj:`Exception`
        )
    """
    sources_path = util.get_sources_dir()
    sources_files = sources_path.glob('*.sources')
    list_files = sources_path.glob('*.list')

    files = []
    errors = {}

    if get_system:
        file = SystemSource()
        files.append(file)
    
    for file in sources_files:
        if file.stem == 'system':
            continue
        source_file  = SourceFile(ident=file.stem)
        try:
            source_file.load_deb_sources()
            files.append(source_file)
        except Exception as err:
            source_file.load_deb_sources()
            errors[file] = err
    
    for file in list_files:
        source_file = SourceFile(ident=file.stem)
        try:
            source_file.load_deb_sources()
            files.append(source_file)
        except Exception as err:
            source_file.load_deb_sources()
            errors[file] = err
    
    return files, errors

def find_file(source_ident):
    """ Finds a SourceFile object containing the ident supplied.

    Arguments:
        :str source_ident: The ident of the source to locate.
    
    Returns:
        The SourceFile object containing a source with the given ident.
    """
    sources = get_all_sources()
    for source in sources:
        if source.ident == source_ident:
            return source.file


def repo_has_source_code(source):
    """ Returns whether a repo has a matching source code repo available.

    Arguments:
        :source Source: The source to find a match for.
    
    Returns:
        Tuplpe(:bool:, :Source:), whether the source has a source-code repo, and
            the matched source code repo.
    """

    all_repos, errors = get_all_sources(get_system=True)

    if source.file.format == 'list':
        for i in [repo for repo in all_repos if repo.types == ['deb-src']]:
            match_uris = source.uris == i.uris
            match_suites = source.suites == i.suites
            match_comps = source.components == i.components
            
            if match_uris and match_suites and match_comps:
                return True, i
        
    elif source.file.format == 'sources':
        if source.types == 'deb-src':
            return False, None

        return True, source
        
    return False, None

def enable_code(source, enabled):
    """ Sets the source code status for the given source.

    Note: This will not save to disk; be sure to use the save method on the 
    returned source's file attribute.

    Arguments:
        :source Source: The source to enable.
        :enabled bool: The state of the source code.
    
    Returns: Tuple:
        :Source: The Source object for the source code repo, or :None:
        :Status: Blank if above is True, or an error message.
    """

    available, repo = repo_has_source_code(source)

    if source.file.format == 'sources':
        if not available:
            return None, 'DEB822 format source is already a source-code repository'
        
        if enabled:
            source.types = 'deb deb-src'
            return source, 'DEB822: Source code enabled'
        else:
            source.types = 'deb'
            return source, 'DEB822: Source code enabled.'
    
    elif source.file.format == 'list':
        append = ''

        if not available:
            repo = source.copy(source_code = True)
            repo.name = f'{repo.name} Source Code'
            source.file.add_source(repo)
            append = 'New source code repo created.'
        
        repo.enabled = enabled
        return repo, f'Legacy: Source code set to {enabled} {append}'
    
    return None, 'Repository format not supported (must be .list or .sources).'
