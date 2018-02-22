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
Data structures that are common across the objects
"""

# Built-in modules

from collections import namedtuple

SystemData = namedtuple('systemData', [
    'sysDescr',     # Detailed text description of the system
    'sysObjectID',  # Vendor's OID identifying the device, which should correspond to make/model
    'sysName',      # Usually either the hostname or the host's FQDN
    'sysLocation'   # Physical location of the device
    ])

Interface = namedtuple('interface', [
    'ifIndex',
    'ifDescr',          # Should include the name of the manufacturer, the product name and the
                        # version of the hardware interface.
    'ifType',           # http://www.alvestrand.no/objectid/1.3.6.1.2.1.2.2.1.3.html
    'ifSpeed',          # Estimate of current bandwidth in bits per second
    'ifPhysAddress',    # MAC address or equivalent
    'ifName',           # As assigned by the local device, for CLI administration
    'ifHighSpeed',      # An estimate of the interface's current bandwidth in units of 1,000,000 bps
    'ifAlias'           # Administrator-configured description string for the interface.
    ])

IpAddress = namedtuple('ipAddress', [
    'ipAddressIfIndex', # The IF-MIB index for the interface on which this address is configured
    'protocol',         # IP protocol version: ipv4 | ipv6
    'address',          # IP address
    'prefixlength',     # integer, 0-128
    'addressType'       # Address type: unicast, multicast or broadcast
    ])

IpAddr = namedtuple('ipAddr', [
    'ipAdEntIfIndex',   # The IP-MIB index for the associated interface
    'ipAdEntAddr',      # The actual IP address
    'ipAdEntNetMask'    # The address' netmask
    ])
