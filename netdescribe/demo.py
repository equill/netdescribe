#!/usr/bin/env python3

"""
Aggregate discovery manager
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

# Local modules
from netdescribe.snmp import device_discovery

# From this package
from netdescribe.utils import create_logger

# Included batteries
import argparse
import logging


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
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    # Set debug logging, if requested
    if args.debug:
        logger = create_logger(logging.DEBUG)
    else:
        logger = create_logger()
    # Perform SNMP discovery on a device and print the result to STDOUT
    print(device_discovery.explore_device(args.hostname, logger, community=args.community))

if __name__ == '__main__':
    basic_demo()
