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
