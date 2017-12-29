#!/usr/bin/env python3

"""
Functions for sending output to STDOUT,
i.e. to the terminal/CLI unless redirected.
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

# From this package
from netdescribe.snmp import device_discovery
from netdescribe.utils import create_logger

class IPInterfaceEncoder(json.JSONEncoder):
    "Render an ipaddress.IPv4Interface object to a serialisable string"
    def default(self, obj):
        if isinstance(obj, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)):
            return obj.with_prefixlen
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def snmp_to_json(target, community, filepath, logger=None):
    """
    Explore a device via SNMP, and write the results to a file in JSON.
    """
    # Ensure we have a logging object.
    # Normally I'd default the loglevel to INFO, but this function will be more
    # useful if its output can be consumed directly, without having to filter
    # out any log messages.
    if logger:
        slogger = logger
    else:
        slogger = create_logger(loglevel="warn")
    # Perform SNMP discovery on a device and write the result to the specified path.
    # Do basic pretty-printing of the output, for human-readability.
    response = device_discovery.explore_device(target, slogger, community=community)
    outfile = open(filepath, "w")
    json.dump(response, outfile, sort_keys=True, indent=4, cls=IPInterfaceEncoder)
    outfile.close()
