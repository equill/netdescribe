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
from netdescribe.snmp.snmp_structures import Interface, IpAddr, IpAddress, SystemData
import netdescribe.utils

# Built-in modules
import collections
import ipaddress
import json
import re

class Mib2:
    "Generic device conforming to SNMP MIB-II"

    def __init__(self, target, engine, auth, logger, sysObjectID=None):
        # SNMP and overhead parameters
        self.target = target
        self.engine = engine
        self.auth = auth
        self.logger = logger
        # Things that can vary between subclasses.
        # Enables us to, e.g, drop 'ifAlias' when querying Brocade MLX to work around Ironware's
        # broken implementation.
        self._if_mib_attrs = [
            # ifTable OIDs
            'ifDescr',
            'ifType',
            'ifSpeed',
            'ifPhysAddress',
            # ifXTable OIDs
            'ifName',
            'ifHighSpeed',
            'ifAlias']
        # Device attributes
        self.system_data = None
        self._ifnumber = None
        self._interfaces = None  # List of Interface namedtuples
        self._ipaddrs = None # List of IpAddr namedtuples
        self._ipaddresses = None # List of IpAddress namedtuples
        # Protected attribute, to capture it if it's supplied
        self._sys_object_id = sysObjectID

    def __get(self, attribute, mib='SNMPv2-MIB'):
        'Convenience function for performing SNMP GET'
        return snmp_get(self.engine, self.auth, self.target, mib, attribute, self.logger)

    def __walk(self, table, row):
        'Convenience function for performing SNMP WALK'
        return snmp_walk(self.engine, self.auth, self.target, table, row, self.logger)

    def identify(self):
        '''
        Return an snmp.snmp_structures.systemData namedtuple.
        Memoised method: if the object already has this data, it won't re-poll the device.
        '''
        hostname = self.target.transportAddr[0]
        self.logger.debug('Returning basic details for %s', hostname)
        # If this data isn't already present, retrieve and set it.
        if not self.system_data:
            self.logger.debug('system_data attribute is null; polling the device for details.')
            sys_descr = self.__get('sysDescr')
            sys_name = self.__get('sysName')
            sys_location = self.__get('sysLocation')
            if not self._sys_object_id:
                self._sys_object_id = self.__get('sysObjectID')
            self.system_data = SystemData(sysName=sys_name,
                                          sysDescr=sys_descr,
                                          sysObjectID=self._sys_object_id,
                                          sysLocation=sys_location)
            self.logger.debug('Retrieved data %s', self.system_data)
        # Return the cached data
        return self.system_data

    def interfaces(self):
        '''
        Return a list of Interface namedtuples.
        If self.interfaces already contains a number of elements matching self._ifnumber,
        it will simply return that list.
        If not, it will query the device to populate that list first.
        '''
        # If it's already sorted, return the contents
        # Note: this approach doesn't work on Linux, because ifNumber isn't implemented there
        if self.interfaces and self._ifnumber and len(self.interfaces) == self._ifnumber:
            return self.interfaces
        # If it's not, get the data.
        # First, find out how many interfaces it should have
        ifnumber = self.__get('ifNumber', mib='IF-MIB')
        if not ifnumber:
            self.logger.error('Failed to retrieve ifNumber')
            return False
        self._ifnumber = ifnumber
        # Now retrieve the interface data
        interfaces = {}
        for row in self._if_mib_attrs:
            for item in self.__walk('IF-MIB', row):
                if item.oid not in interfaces:
                    interfaces[item.oid] = collections.defaultdict(str)
                interfaces[item.oid][row] = item.value
        # Having retrieved the data, create the list
        interfacelist = []
        for index, details in interfaces.items():
            interfacelist.append(Interface(ifIndex=index,
                                           ifDescr=details['ifDescr'],
                                           ifType=details['ifType'],
                                           ifSpeed=details['ifSpeed'],
                                           ifPhysAddress=details['ifPhysAddress'],
                                           ifName=details['ifName'],
                                           ifHighSpeed=details['ifHighSpeed'],
                                           ifAlias=details['ifAlias']))
        self._interfaces = interfacelist
        # Return the data we fetches, but as it's cached in the object
        return self.interfaces

    def ip_addresses(self):
        '''
        Return the device´s IP address table, as a list of ipAddress namedtuples.
        Polls the preferred, but less widely-implemented, ipAddressTable.
        If this isn't already populated, queries the device first.
        NB: Covers both IPv4 and IPv6.
        '''
        # If we already have this data, just return it
        if self._ipaddresses:
            return self._ipaddresses
        # We don't already have it. Fetch it, then return it.
        # First, fetch the data.
        self.logger.debug('Retrieving IP addresses from ipAddressTable')
        acc = {}    # Intermediate accumulator for building up a map
        # acc structure:
        # - index = SNMP index for ipAddressTable, e.g. ipv4."192.168.124.1"
        #   - index = SNMP index
        #   - address = IP address
        #   - protocol = IP protocol version, i.e. ipv4 or ipv6
        #   - prefixlength = integer, 0-32
        #   - type = address type: unicast, multicast or broadcast
        self.logger.debug('Retrieving indices and addresses')
        # ipAddressIfIndex
        # - the value is the relevant interface's IF-MIB index
        # - the OID/index contains the address type (IPv4 vs IPv6) and the address itself,
        #   separated by a dot.
        #   The address is wrapped in quotes, hence the offset indices at each end.
        for item in self.__walk('IP-MIB', 'ipAddressIfIndex'):
            protocol = re.split('\.', item.oid)[0]
            acc[item.oid] = {'ipAddressIfIndex': item.value,
                             # Extract the address and protocol from the OID/index
                             'protocol': protocol,
                             'address': item.oid[(len(protocol) + 2):][0:-1]}
            self.logger.debug('Initialising address in the accumulator with %s', acc[item.oid])
        self.logger.debug('Retrieving prefix lengths')
        # Prefix length / ipAddressPrefix
        # The value for this OID contains all sorts of crap prepended to the actual prefix-length,
        # so we have to break it up and extract the last element from the resulting list.
        for item in self.__walk('IP-MIB', 'ipAddressPrefix'):
            prefixlength = re.split('\.', item.value)[-1]
            acc[item.oid]['prefixlength'] = prefixlength
            self.logger.debug('Accumulated prefixlength %s for address %s',
                              prefixlength, item.oid)
        # Types - unicast, anycast or broadcast.
        # No multicast here; these are handled in another table again.
        self.logger.debug('Retrieving address types')
        for item in self.__walk('IP-MIB', 'ipAddressType'):
            acc[item.oid]['addressType'] = item.value
            self.logger.debug('Accumulated type %s for address %s', item.value, item.oid)
        # Populate self._ipaddresses
        self._ipaddresses = [IpAddress(ipAddressIfIndex=details['ipAddressIfIndex'],
                                       protocol=details['protocol'],
                                       address=details['address'],
                                       prefixlength=details['prefixlength'],
                                       addressType=details['addressType'])
                             for _, details in acc.items()]
        # Now return it
        return self._ipaddresses

    def ip_addresses_to_dict(self):
        '''
        Convert the list of ipAddress namedtuples to a dict whose keys
        are the ipAddressIfIndex value, i.e. the IF-MIB index for that interface.
        Intended as a helper function for combining addresses with interfaces.
        '''
        acc = collections.defaultdict(list)
        for address in self._ipaddresses:
            # When queried for ipAddressPrefix, Brocade Ironware returns an upraised middle finger
            # in the form of SNMPv2-SMI::zeroDotZero.
            # Catch and handle this case.
            if address.prefixlength == 'SNMPv2-SMI::zeroDotZero':
                prefix = 0
            else:
                prefix = address.prefixlength
            # Now assemple it
            acc[address.ipAddressIfIndex].append({'protocol': address.protocol,
                                                  'address': address.address,
                                                  'prefixLength': prefix,
                                                  'addressType': address.addressType})
        return acc

    def ip_addrs(self):
        '''
        Return the device´s IP address table, as a list of ipAddr namedtuples.
        Derived from the deprecated but still widely-used ipAddrTable.
        If this isn't already populated, queries the device first.
        NB: Ipv4-only, by definition.
        '''
        # If we already have this data, just return it
        if self._ipaddrs:
            return self._ipaddrs
        # We don't already have it. Fetch it, then return it.
        # First, fetch the data.
        acc = {}    # Intermediate accumulator for building up a map
        # acc structure:
        # - index = SNMP index for ipAddressTable, e.g. ipv4."192.168.124.1"
        #   - index = SNMP index
        #   - address = IP address
        #   - protocol = IP protocol version, i.e. ipv4 or ipv6
        #   - prefixlength = integer, 0-32
        #   - type = address type: unicast, multicast or broadcast
        self.logger.debug('Retrieving IPv4 addresses from ipAddrTable')
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
        # Assemble the fetched data into a list of IpAddr namedtuples
        self._ipaddrs = [IpAddr(ipAdEntAddr=details['address'],
                                ipAdEntIfIndex=details['index'],
                                ipAdEntNetMask=details['netmask'])
                         for index, details in acc.items()]
        # Now return it
        return self._ipaddrs

    def ip_addrs_to_dict(self):
        '''
        Convert the list of ipAddr namedtuples to a dict whose keys are the ipAdEntIfIndex value,
        i.e. the IF-MIB index for the associated interface.
        Converts the netmask to a prefix-length, for consistency with the ipAddresses table.
        Intended as a helper function for combining addresses with interfaces.
        '''
        result = collections.defaultdict(list)
        for addr in self._ipaddrs:
            # Derive the prefixlength, and get a simpler varname for address while we're at it.
            (address, prefixlength) = re.split(
                '/',
                ipaddress.IPv4Interface('{}/{}'.format(addr.ipAdEntAddr,
                                                       addr.ipAdEntNetMask)).with_prefixlen)
            # Assemble and insert the actual entry
            result[addr.ipAdEntIfIndex].append({'protocol': 'ipv4',    # IPv4-only table
                                                'address': address,
                                                'prefixLength': prefixlength,
                                                'addressType': 'unknown'})
        return result

    def ifaces_with_addrs(self):
        '''
        Return a dict of dicts:
        - convert the list of interface namedtuples to a dict whose index is ifName
        - add an attribute 'addresses' whose value is a list of dicts representing addresses.
        Output format uses the following structure of keys:
        - <ifName>
            - ifIndex
            - ifDescr
            - ifType
            - ifSpeed
            - ifPhysAddress
            - ifName
            - ifHighSpeed
            - ifAlias
            - addresses
                - protocol
                - address
                - prefixLength
                - addressType
        '''
        result = {} # Accumulator for the return value
        # Which addresses store should we use?
        # Prefer the newer table
        if self._ipaddresses:
            addresslist = self.ip_addresses_to_dict()
        # ...but use the deprecated one, if that's all we have.
        elif self._ipaddrs:
            addresslist = self.ip_addrs_to_dict()
        # Failing all else, provide a last-resort default.
        # This simplifies the code in the next section, by removing the need for a conditional.
        else:
            addresslist = collections.defaultdict(list)
        # Now iterate over the interfaces
        for iface in self._interfaces:
            # Assemble and insert the entry
            result[iface.ifName] = {'ifIndex': iface.ifIndex,
                                    'ifDescr': iface.ifDescr,
                                    'ifType': iface.ifType,
                                    'ifSpeed': iface.ifSpeed,
                                    'ifPhysAddress': iface.ifPhysAddress,
                                    'ifName': iface.ifName,
                                    'ifHighSpeed': iface.ifHighSpeed,
                                    'ifAlias': iface.ifAlias,
                                    'addresses': addresslist[iface.ifIndex]}
        return result

    def as_dict(self):
        'Return the object´s contents as a dict'
        return {'system': {'sysDescr': self.system_data.sysDescr,
                           'sysObjectID': self.system_data.sysObjectID,
                           'sysName': self.system_data.sysName,
                           'sysLocation': self.system_data.sysLocation},
                'interfaces': self.ifaces_with_addrs()}

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
        self.ip_addrs()
        self.ip_addresses()
        return True
