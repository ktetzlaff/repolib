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

This is a library for handling files which contain sources.
"""

from typing import Dict, List, Tuple
from pathlib import Path

from .source import Source
from .deb import DebLine
from . import util

class SourceFileError(Exception):
    """ Exception from a source file."""

    def __init__(self, *args, code:int = 1, **kwargs):
        """Exception with a source file

        Arguments:
            :code int, optional, default=1: Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code: int = code

class SourceFile:
    """ A class for handling source files (files which contain sources).
    
    Attributes:
        :ident str: the name of the file (less the extension).
        :comments dict[int, str]: A dict of comments in the file, with line
            numbers as the keys.
        :sources list[Source]: A list of DEB822-format sources in the file.
        :legacy_sources dict[int, DebLine]: A list of legacy-format sources and
            their line numbers.
        :source_path Path: The Path object for the file.
        :legacy bool: Whether the source contains legacy deb sources.
    """

    def __init__(self, ident: str = ''):
        """
        Arguments:
            :str ident: The filename of the file (without the extension)
        """
        self.ident: str = ident
        self.comments: Dict[int, str] = {}
        self.sources: List[Source] = []
        self.legacy_sources: Dict[int, DebLine] = {}
        self.source_path: Path
        self.legacy: bool = False 
    
    def parse_comments(self, source_data: List[str]) -> List[str]:
        """ Extracts comments from the source file and saves them.

        Arguments:
            :source_data list: The contents of the source file.
        """
        line_num: int = 0
        for line in source_data:
            # Find commented out lines
            if line.startswith('#'):
                # Exclude disabled legacy deblines.
                name_line = 'X-Repolib-Name' in line
                if not util.validate_debline(line) and not name_line:
                    self.comments[line_num] = line
                    source_data[line_num] = ''
            
            # Empty lines count as comments
            if line == '\n':
                self.comments[line_num] = line

            line_num += 1
        
        return source_data
    
    def parse_legacy(self, source_data: List[str]):
        """ Parse the legacy deblines from the file and save their line numbers

        Arguments:
            :source_data list: The contents of the source file.
        """
        line_num: int = 0
        for line in source_data:
            enabled: bool = True
            src: bool = False

            # Find Repolib names
            if 'X-Repolib-Name' in line:
                name = ':'.join(line.split(':')[1:])
                name = name.strip()
            
            # disable commented lines
            if line.startswith('#'):
                enabled = False
                line = line.replace('#', '')
            
            print(line)
            if util.validate_debline(line.strip()):
                source = DebLine(line)
                source.enabled = enabled
                self.legacy_sources[line_num] = source
            
            line_num += 1
    
    def parse_file(self, ident: str = ''):
        """ Parses the contents of the file. 
        
        Optionally use ident if one hasn't been supplied yet.

        Arguments:
            :ident str: The ident of the file. Does not override the main ident
                unless one hasn't been provided.
        """
        if not self.ident:
            self.ident = ident
        
        filestem: str = self.ident
        if ident:
            filestem: str
        
        if not filestem:
            raise SourceFileError('No filename provided to load.')

        self.source_path = util.get_source_path(filestem)

        if self.source_path.suffix == '.list':
            self.legacy = True

        with open(self.source_path, 'r') as source_file:
            source_list = source_file.readlines()
        
        source_list = self.parse_comments(source_list)
        
        if self.legacy:
            self.parse_legacy(source_list)
        