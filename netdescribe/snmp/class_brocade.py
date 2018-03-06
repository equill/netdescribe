#!/usr/bin/env python3

#   Copyright [2018] [James Fleming <james@electronic-quill.net]
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

"""
Class for querying Brocade hosts via SNMP
"""

# Local modules

from netdescribe.snmp import class_mib2

class Brocade(class_mib2.Mib2):
    "Generic Linux device"
    def __init__(self, target, engine, auth, logger, sysObjectID=None):
        class_mib2.Mib2.__init__(self, target, engine, auth, logger, sysObjectID=None)
        # Drop 'ifAlias' when querying Brocade MLX to work around Ironware's
        # broken implementation.
        self._if_mib_attrs = [
            # ifTable OIDs
            'ifDescr',
            'ifType',
            'ifSpeed',
            'ifPhysAddress',
            # ifXTable OIDs
            'ifName',
            'ifHighSpeed']

    def discover(self):
        'Perform full discovery on this device, and report on the result.'
        self.identify()
        self.interfaces()
        self.ip_addresses()
        return True