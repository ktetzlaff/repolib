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

from os import name
import string

class ParseDebError(Exception):
    """ Exceptions related to parsing deb lines."""

    def __init__(self, *args, code=1, **kwargs):
        """Exceptions related to parsing deb lines.

        Arguments:
            code (:obj:`int`, optional, default=1): Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code = code

def debsplit(line:str) -> list:
    """ improved string.split() with support for things like [] options. 
    
    Adapted from python-apt

    Arguments:
        line(str): The line to split up.
    """
    line:str = line.strip()
    parts:list = []
    temp:str = ''

    # parsing for within [...]
    brkt_found: bool = False
    space_found: bool = False

    for i in range(len(line)):
        if line[i] == '[':
            brkt_found = True
            temp += line[i]
        elif line[i] == ']':
            brkt_found = False
            temp += line[i]
        elif space_found and not line[i].isspace():
            space_found = False
            parts.append(temp)
            temp = line[i]
        elif line[i].isspace() and not brkt_found:
            space_found = True
        else:
            temp += line[i]
        
        if len(temp) > 0:
            parts.append(temp)
        
        return parts

def parse_name_ident(comment:str) -> tuple:
    """ Find a Repolib name within the given comment string.

    The name should be headed with "X-Repolib-Name:" and is not space terminated.
    The ident should be headed with "X-Repolib-Ident:" and is space terminated.

    Either field ends at the end of a line, or at a subsequent definition of a
    different field, or at a subsequent ' #' substring. Additionally, the ident
    field ends with a subsequent space.

    Arguments:
        comment (str): The comment to search within.
    
    Returns:
        (name, ident, comment):
            name (str): The detected name, or None
            ident (str): The detected ident, or None
            comment (str): The string with the name removed
    """
    # Clean up the leading comment markers
    while True:
        comment = comment.strip('#')
        comment = comment.strip()
        if not comment.startswith('#'):
            break

    parts: list = comment.split()
    name_found = False
    ident_found = False
    name:str = ''
    ident:str = ''
    comment:str = ''
    print(parts)
    for item in parts:
        print(item)
        print(f'Name: "{name}"; Ident: "{ident}"; Comment: "{comment}"')
        print(f'Parsing name: {name_found}; Parsing ident: {ident_found}')
        item_is_name = item.strip('#') == 'X-Repolib-Name:'
        item_is_ident = item.strip('#') == 'X-Repolib-Ident:'
        
        if '#' in item and not item_is_name and not item_is_ident:
            name_found = False
            ident_found = False
        
        elif item_is_name:
            name_found = True
            ident_found = False
            continue
        
        elif item_is_ident:
            name_found = False
            ident_found = True
            continue
        
        if name_found and not item_is_name:
            name += f'{item} '
            continue
        
        elif ident_found and not item_is_ident:
            ident += f'{item}'
            ident_found = False
            continue
        
        elif not name_found and not ident_found:
            c = item.strip('#')
            comment += f'{c} '

    name = name.strip()
    ident = ident.strip()
    comment = comment.strip()

    return name, ident, comment


class ParseDeb:
    """ Parsing for source entries. 

    Contains parsing helpers for one-line format sources.
    """

    def __init__(self) -> None:
        self.last_line: str = ''
        self.last_line_valid: bool = False
        self.curr_line: str = ''
        self.curr_line_valid: str = False
    
    def parse_line(self, line:str) -> dict:
        """ Parse a deb line into its individual parts.

        Arguments:
            line (str): The line input to parse
        
        Returns:
            (dict): a dict containing the requisite data.
        """
        self.last_line = self.curr_line
        self.last_line_valid = self.curr_line_valid
        self.curr_line = line.strip()

        parts:list = []

        line_is_comment = self.curr_line == '#'
        line_is_empty = self.curr_line == ''
        if line_is_comment or line_is_empty:
            raise ParseDebError(f'Current line "{self.curr_line}" is empty')
        
        line_parsed: dict = {}
        line_parsed['enabled'] = True
        line_parsed['comments'] = ''
        
        if line.startswith('#'):
            line_parsed['enabled'] = False
            parts = line[1:].split()
            if not parts[0] in ['deb', 'deb-src']:
                raise ParseDebError(f'Current line "{self.curr_line}" is invalid')
            
            else:
                # Remove the leading comment marker
                line = line[1:]
        
        comments = line.find('#')
        if comments > 0:
            raw_comments = line[i + 1]


