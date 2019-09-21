#!/usr/bin/env python3

"""
Example usage of the Netdescribe library.
Performs discovery, and sends JSON-formatted output to either standard out or a file,
depending on whether the --file parameter is supplied.
"""


#   Copyright [2017] [James Fleming <james@electronic-quill.net]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# pylint: disable=wrong-import-order

# From this package
import netdescribe.files
import netdescribe.stdout
from netdescribe.utils import create_logger

# Included batteries
import argparse


def basic_demo():
    """
    Enable this to be run as a CLI script, as well as used as a library.
    Mostly intended for testing or a basic demo.
    """
    # Get the command-line arguments
    parser = argparse.ArgumentParser(description='Perform SNMP discovery on a host, \
    returning its data in a single structure.')
    parser.add_argument('hostname',
                        type=str,
                        help='The hostname or address to perform discovery on')
    parser.add_argument('--community',
                        type=str,
                        action='store',
                        dest='community',
                        default='public',
                        help='SNMP v2 community string')
    parser.add_argument('--file',
                        type=str,
                        action='store',
                        dest='filepath',
                        default=None,
                        help='Filepath to write the results to. If this is not specified, \
                        STDOUT will be used.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    # Set debug logging, if requested
    if args.debug:
        logger = create_logger(loglevel="debug")
    # Normal logging if we're writing to a file
    elif args.filepath:
        logger = create_logger()
    # Suppress INFO output if we're returning it to STDOUT:
    # don't require the user to filter the output to make it useful.
    else:
        logger = create_logger(loglevel="warning")
    # Perform SNMP discovery on a device,
    # sending the result to STDOUT or a file, depending on what the user told us.
    if args.filepath:
        netdescribe.files.snmp_to_json(args.hostname, args.community, args.filepath, logger)
    else:
        netdescribe.stdout.snmp_to_json(args.hostname, args.community, logger)

if __name__ == '__main__':
    basic_demo()
