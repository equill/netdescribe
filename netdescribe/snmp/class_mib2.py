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
Generic SNMP MIB-II object
"""

# Local modules
from netdescribe.snmp.snmp_functions import snmp_get, snmp_walk
import netdescribe.utils

# Built-in modules
import ipaddress
import json
import re

class Mib2:
    "Generic device conforming to SNMP MIB-II"

    def __init__(self, target, engine, auth, logger, sysObjectID=None):
        self.target = target
        self.engine = engine
        self.auth = auth
        self.logger = logger
        self.sys_name = None
        self.sys_descr = None
        self.sys_object_id = sysObjectID
        self.sys_location = None
        self.network = None

    def __get(self, attribute):
        'Convenience function for performing SNMP GET'
        return snmp_get(self.engine, self.auth, self.target, 'SNMPv2-MIB', attribute, self.logger)

    def __walk(self, table, row):
        'Convenience function for performing SNMP WALK'
        return snmp_walk(self.engine, self.auth, self.target, table, row, self.logger)

    def identify(self):
        '''
        Extract some general identifying characteristics.
        Return a dict:
        - sysName       # Hostname. Should be the FDQN, but don't count on it.
        - sysDescr      # Detailed text description of the system.
        - sysObjectID   # Vendor's OID identifying the device.
        '''
        hostname = self.target.transportAddr[0]
        self.logger.debug('Returning basic details for %s', hostname)
        if not self.sys_name:
            self.sys_name = self.__get('sysName')
        self.sys_descr = self.__get('sysDescr')
        self.sys_location = self.__get('sysLocation')
        if not self.sys_object_id:
            self.sys_object_id = self.__get('sysObjectID')
        returnval = {'sysName': self.sys_name,
                     'sysDescr': self.sys_descr,
                     'sysObjectID': self.sys_object_id,
                     'sysLocation': self.sys_location}
        self.logger.debug('Retrieved data %s', returnval)
        return returnval

    def _get_iface_addr_map(self):
        '''
        Extract a mapping of addresses to interfaces, derived from the deprecated but still
        widely-used ipAddrTable.
        This only returns IPv4 addresses for now.
        Return a dict:
        - interface index in ifTable
            - list of ipaddress interface objects
        '''
        self.logger.debug('Extracting a mapping of addresses to interfaces from ipAddressTable')
        # SNMP returns this to us by address not interface.
        # Thus, we have to build an address-oriented dict first, then assemble the final result.
        acc = {}    # Intermediate accumulator for building up a map
        # acc structure:
        # - index = SNMP index for ipAddressTable, e.g. ipv4."192.168.124.1"
        #   - index = SNMP index
        #   - address = IP address
        #   - protocol = IP protocol version, i.e. ipv4 or ipv6
        #   - prefixlength = integer, 0-32
        #   - type = address type: unicast, multicast or broadcast
        # Addresses
        self.logger.debug('Retrieving ddresses')
        for item in self.__walk('IP-MIB', 'ipAdEntAddr'):
            self.logger.debug('Initialising address {} in the accumulator with index {}'.format(
                item.value, item.oid))
            acc[item.oid] = {'address': item.value}
        self.logger.debug('Retrieving indices')
        for item in self.__walk('IP-MIB', 'ipAdEntIfIndex'):
            self.logger.debug('Augmenting {} with interface index {}'.format(item.value, item.oid))
            acc[item.oid]['index'] = item.value
        self.logger.debug('Retrieving netmasks')
        for item in self.__walk('IP-MIB', 'ipAdEntNetMask'):
            self.logger.debug('Augmenting {} with netmask {}'.format(item.value, item.oid))
            acc[item.oid]['netmask'] = item.value
        # Build the return structure
        result = {}
        for addr, details in acc.items():
            self.logger.debug('Examining address %s for the address map, with details %s',
                              addr, details)
            # Build the interface object
            address = ipaddress.IPv4Interface('%s/%s' % (details['address'], details['netmask']))
            self.logger.debug('Inferred address %s', address)
            # Ensure there's a key in the dict for this interface
            if details['index'] not in result:
                result[details['index']] = []
            # Add this address to its interface's address-list
            result[details['index']].append(address)
        # Return it
        self.logger.debug('Returning interface address map: %s', result)
        return result

    def _get_iface_address_map(self):
        '''
        Extract a mapping of addresses to interfaces, derived from the ipAddressTable OID.
        This one is preferred over the deprecated ipAddrTable, but less widely implemented.
        Return a dict:
        - interface index in ifTable
            - list of ipaddress interface objects
        '''
        self.logger.debug('Extracting a mapping of addresses to interfaces from ipAddressTable')
        # SNMP returns this to us by address not interface.
        # Thus, we have to build an address-oriented dict first, then assemble the final result.
        acc = {}    # Intermediate accumulator for building up a map
        # acc structure:
        # - index = SNMP index for ipAddressTable, e.g. ipv4."192.168.124.1"
        #   - index = SNMP index
        #   - address = IP address
        #   - protocol = IP protocol version, i.e. ipv4 or ipv6
        #   - prefixlength = integer, 0-32
        #   - type = address type: unicast, multicast or broadcast
        # Addresses
        self.logger.debug('Retrieving indices and addresses')
        for item in self.__walk('IP-MIB', 'ipAddressIfIndex'):
            protocol = item.oid[:4]
            acc[item.oid] = {'index': item.value,
                             'address': item.oid[6:][0:-1],
                             'protocol': protocol}
            self.logger.debug('Initialising address in the accumulator with %s', acc[item.oid])
        self.logger.debug('Retrieving prefix lengths')
        for item in self.__walk('IP-MIB', 'ipAddressPrefix'):
            prefixlength = re.split('\.', item.value)[-1]
            acc[item.oid]['prefixlength'] = prefixlength
            self.logger.debug('Accumulated prefixlength %s for address %s',
                              prefixlength, item.oid)
        # Types
        self.logger.debug('Retrieving address types')
        for item in self.__walk('IP-MIB', 'ipAddressType'):
            acc[item.oid]['type'] = item.value
            self.logger.debug('Accumulated type %s for address %s', item.value, item.oid)
        # Build the return structure
        result = {}
        for addr, details in acc.items():
            self.logger.debug('Examining address %s, with details %s', addr, details)
            # Is this the kind of address we want?
            if details['type'] != 'unicast':
                self.logger.debug('Rejecting non-unicast address %s with type %s',
                                  addr, details['type'])
            # Build the interface object
            # Which IP version?
            if details['protocol'] == 'ipv4':
                address = ipaddress.IPv4Interface('%s/%s' % (details['address'],
                                                             details['prefixlength']))
            else:
                address = ipaddress.IPv6Interface('%s/%s' % (details['address'],
                                                             details['prefixlength']))
            self.logger.debug('Inferred address %s', address)
            # Ensure there's a key in the dict for this interface
            if details['index'] not in result:
                result[details['index']] = []
            # Add this address to its interface's address-list
            result[details['index']].append(address)
        # Return it
        self.logger.debug('Returning interface address map: %s', result)
        return result

    def interfaces(self):
        '''
        Extract the device's network details, and return them as a nested structure:
        - interfaces
            - <SNMP index>
                - ifName    # Short name of the interface, in contrast to ifDescr
                - ifDescr   # Detailed text description of the interface
                - ifAlias   # Description string as configured for this interface.
                - ifType    # IANA-specified interface type
                - ifSpeed   # reports the max speed in bits/second.
                            # If a 32-bit gauge is too small to report the speed, this should be
                            # set to the max possible value (4,294,967,295) and ifHighSpeed must
                            # be used instead.
                - ifHighSpeed   # ifHighSpeed is an estimate of the interface's current bandwidth
                                # in units of 1,000,000 bits per second. Zero for subinterfaces
                                # with no concept of bandwidth.
                - ifPhysAddress    # E.g. MAC address for an 802.x interface
        - ipIfaceAddrMap      # Mapping of addresses to interface indices
            - interface index (relative to ifTable)
                - list of dicts:
                    - address = IP address for interface
                    - netmask = netmask for interface address
        '''
        # If we've already discovered this thing's networking details, return what we already know
        if self.network and 'interfaces' in self.network:
            self.logger.debug('Already discovered network interfaces for this device')
            return self.network
        # If we haven't, carry on with discovery
        self.logger.debug('Discovering network interfaces for host %s',
                          self.target.transportAddr[0])
        network = {'interfaces': {}}
        # Basic interface details
        for row in ['ifDescr', # ifTable OIDs
                    'ifType',
                    'ifSpeed',
                    'ifPhysAddress',
                    # ifXTable OIDs
                    'ifName',
                    'ifHighSpeed',
                    'ifAlias']:
            for item in self.__walk('IF-MIB', row):
                if item.oid not in network['interfaces']:
                    network['interfaces'][item.oid] = {}
                network['interfaces'][item.oid][row] = item.value
        # Map addresses to interfaces
        self.logger.debug('Mapping addresses to interfaces')
        # Use the deprecated table by default
        network['ipIfaceAddrMap'] = self._get_iface_addr_map()
        self.network = network
        return self.network

    def as_dict(self):
        'Return the object´s contents as a dict'
        return {'sysName': self.sys_name,
                'sysDescr': self.sys_descr,
                'sysObjectID': self.sys_object_id,
                'sysLocation': self.sys_location,
                'network': self.network}

    def as_json(self):
        'Return a print representation of this object'
        return json.dumps(self.as_dict(),
                          indent=4,
                          sort_keys=True,
                          cls=netdescribe.utils.IPInterfaceEncoder)

    def __str__(self):
        'Return a print representation of this object'
        return self.as_json()

    def discover(self):
        'Perform full discovery on this device, and report on the result.'
        self.identify()
        self.interfaces()
        return True
