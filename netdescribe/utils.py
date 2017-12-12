#!/usr/bin/env python3

"""
General utilities
"""

# Included batteries
import logging
import sys

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
