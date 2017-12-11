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
from snmp import device_discovery

# Included batteries
import argparse
import logging
import sys


def create_logger(loglevel=logging.INFO):
    """
    Create a logging object, suitable for passing to the discovery functions.
    """
    # Creat the basic object, and set its base loglevel
    logger = logging.getLogger('netdescribe')
    logger.setLevel(logging.DEBUG)
    # Create and configure a console handler, and add it to the logger
    chandler = logging.StreamHandler(stream=sys.stdout)
    chandler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    chandler.setLevel(loglevel)
    logger.addHandler(chandler)
    # Return the logger we created
    return logger


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
    print(device_discovery.exploreDevice(args.hostname, logger, community=args.community))

if __name__ == '__main__':
    basic_demo()
