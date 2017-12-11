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


# Configure logging
# Basic setup
#
LOGLEVEL = logging.INFO
LOGGER = logging.getLogger('netdescribe')
#
# Create console handler
# create and configure console handler, and add it to the logger
CH = logging.StreamHandler(stream=sys.stdout)
CH.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
CH.setLevel(LOGLEVEL)
LOGGER.setLevel(LOGLEVEL)
LOGGER.addHandler(CH)



# Enable this to be run as a CLI script, as well as used as a library.
# Mostly used for testing, at this stage.
if __name__ == '__main__':
    # Get the command-line arguments
    PARSER = argparse.ArgumentParser(description='Perform SNMP discovery on a host, \
    returning its data in a single structure.')
    PARSER.add_argument('hostname', type=str,
                        help='The hostname or address to perform discovery on')
    PARSER.add_argument('--community', type=str, action='store',
                        dest='community', default='public', help='SNMP v2 community string')
    PARSER.add_argument('--debug', action='store_true', help='Enable debug logging')
    ARGS = PARSER.parse_args()
    # Set debug logging, if requested
    if ARGS.debug:
        LOGGER.setLevel(logging.DEBUG)
        CH.setLevel(logging.DEBUG)
    # Perform SNMP discovery on a device
    DEVICE = {'snmp': device_discovery.exploreDevice(ARGS.hostname,
                                                     LOGGER,
                                                     community=ARGS.community,)}
    print(DEVICE)
