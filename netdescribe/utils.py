#!/usr/bin/env python3

"""
General utilities
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

# Included batteries
import ipaddress
import json
import logging
import sys


def create_logger(loglevel="info"):
    """
    Create a logging object, suitable for passing to the discovery functions.
    'loglevel" should be a string, with a value selected from
    - critical
    - error
    - warning
    - info
    - debug
    """
    loglevels = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }
    # Creat the basic object, and set its base loglevel
    logger = logging.getLogger('netdescribe')
    # Configure the logger only if we haven't already done this
    if not logger.hasHandlers():
        logger.setLevel(loglevels[loglevel])
        # Create and configure a console handler, and add it to the logger
        chandler = logging.StreamHandler(stream=sys.stdout)
        chandler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
        chandler.setLevel(loglevels[loglevel])
        logger.addHandler(chandler)
    # Return the logger we created
    return logger


class IPInterfaceEncoder(json.JSONEncoder):
    """
    Render an ipaddress.IPv4Interface object to a serialisable string.
    Enable rendering interface objects in JSON.
     """
    def default(self, obj):
        # Handle instances of IPv4Interface and IPv6Interface
        if isinstance(obj, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)):
            return obj.with_prefixlen
        # Fall back to the base class's default behaviour for anything else
        return json.JSONEncoder.default(self, obj)
