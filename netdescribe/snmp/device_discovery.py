#!/usr/bin/env python3

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

"""
Perform discovery on an individual host, using SNMP version 2c
"""

# Third-party libraries
import pysnmp.hlapi

# From this package
from netdescribe.utils import create_logger

# Included batteries
from collections import namedtuple
import ipaddress
import json
import re
import sys


# Data structures
SnmpDatum = namedtuple('snmpDatum', ['oid', 'value'])


# Utility functions

#def snmp_get(hostname, mib, attr, community, logger, port=161):
def snmp_get(engine, auth, target, mib, attr, logger):
    '''
    Perform an SNMP GET for a single OID or scalar attribute.
    Return only the value.
    '''
    logger.debug('Getting %s::%s from %s', mib, attr, target.transportAddr[0])
    # Use pysnmp to retrieve the data
    obj = pysnmp.hlapi.ObjectIdentity(mib, attr, 0)
    oid = pysnmp.hlapi.ObjectType(obj)
    cmd = pysnmp.hlapi.getCmd(engine, auth, target, pysnmp.hlapi.ContextData(), oid)
    error_indication, error_status, error_index, var_binds = next(cmd)
    # Handle the responses
    returnval = False
    if error_indication:
        logger.error(error_indication)
    elif error_status:
        logger.error('%s at %s' % (error_status.prettyPrint(),
                                   error_index and var_binds[int(error_index) - 1][0] or '?'))
    # If we actually got something, return it as an SnmpDatum
    else:
        returnval = var_binds[0][1].prettyPrint()
    return returnval

def snmp_walk(engine, auth, target, mib, attr, logger):
    '''
    Walk an SNMP OID.
    Return a list of SnmpDatum namedtuples.
    '''
    logger.debug('Walking %s::%s on %s', mib, attr, target.transportAddr[0])
    # Build and execute the command
    obj = pysnmp.hlapi.ObjectIdentity(mib, attr)
    oid = pysnmp.hlapi.ObjectType(obj)
    cmd = pysnmp.hlapi.nextCmd(engine,
                               auth,
                               target,
                               pysnmp.hlapi.ContextData(),
                               oid,
                               lexicographicMode=False)
    returnval = []
    for (error_indication, error_status, error_index, var_binds) in cmd:
        # Handle the responses
        if error_indication:
            logger.error(error_indication)
        elif error_status:
            logger.error('%s at %s',
                         error_status.prettyPrint(),
                         error_index and var_binds[int(error_index) - 1][0] or '?')
        # If we actually got something, return it as an SnmpDatum
        else:
            for var in var_binds:
                # Extract the index values.
                # We're breaking down 'IF-MIB::ifType.530' into (row='ifType', index='530').
                # This relies on 'lookupMib=True', to translate numeric OIDs into textual ones.
                keys = re.split('\.', re.split('::', var[0].prettyPrint())[1], maxsplit=1)
                #row = keys[0]
                index = keys[1]
                # Now get the value
                val = var[1].prettyPrint()
                # Update the results table
                logger.debug('%s = %s', index, val)
                returnval.append(SnmpDatum(oid=index, value=val))
    return returnval


# Functions to actually get the data

def identify_host(engine, auth, target, logger):
    '''
    Extract some general identifying characteristics.
    Return a dict:
    - sysName       # Hostname. Should be the FDQN, but don't count on it.
    - sysDescr      # Detailed text description of the system.
    - sysObjectID   # Vendor's OID identifying the device.
    '''
    hostname = target.transportAddr[0]
    logger.debug('Querying %s for general details', hostname)
    data = {}
    for attr in ['sysName',
                 'sysDescr',
                 'sysObjectID']:
        response = snmp_get(engine, auth, target, 'SNMPv2-MIB', attr, logger)
        if response:
            data[attr] = response
        else:
            logger.critical('Failing to retrieve even basic data about %s' % hostname)
            return None
    return data

def get_if_stack_table(engine, auth, target, logger):
    '''
    Extract IF-MIB::ifStackTable from a device, per
    http://www.net-snmp.org/docs/mibs/ifMIBObjects.html
    and return it as a dict, where the key is the higher layer, and
    the value is the lower.
    '''
    logger.debug('Attempting to query %s for ifStackTable', target.transportAddr[0])
    rawdata = snmp_walk(engine, auth, target, 'IF-MIB', 'ifStackStatus', logger)
    logger.debug('rawdata: %s', rawdata)
    if rawdata:
        data = {}
        for datum in rawdata:
            logger.debug("Upper: %s. Lower: %s." % (datum.oid, datum.value))
            data[datum.oid] = datum.value
        logger.debug('ifStackTable: %s', data)
    else:
        data = None
    return data

def get_inv_stack_table(stack):
    '''
    Generate a mapping of interfaces to their subinterfaces,
    based on the dict returned by get_if_stack_table.
    Return a dict:
    - key = SNMP index of an interface
    - value = list of indices of inter
    '''
    data = {}
    # Get the flat map
    # This returns a dict:
    # - SNMP index of parent interface
    # - list of indices of subinterfaces of that parent
    for upper, lower in stack.items():
        if lower not in data:
            data[lower] = []
        data[lower].append(upper)
    # Now turn that into a nested dict, so we have all the interdependencies mapped.
    # Start at subinterface '0', because that's how SNMP identifies "no interface here."
    return data

def get_iface_addr_map(engine, auth, target, logger):
    '''
    Extract a mapping of addresses to interfaces.
    Return a dict:
    - interface index in ifTable
        - list of ipaddress interface objects
    '''
    logger.debug('Extracting a mapping of addresses to interfaces')
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
    logger.debug('Indices and addresses')
    for item in snmp_walk(engine, auth, target, 'IP-MIB', 'ipAddressIfIndex', logger):
        protocol = item.oid[:4]
        acc[item.oid] = {'index': item.value,
                         'address': item.oid[6:][0:-1],
                         'protocol': protocol}
        logger.debug('Initialising address in the accumulator with %s', acc[item.oid])
    logger.debug('Prefix lengths')
    for item in snmp_walk(engine, auth, target, 'IP-MIB', 'ipAddressPrefix', logger):
        prefixlength = re.split('\.', item.value)[-1]
        acc[item.oid]['prefixlength'] = prefixlength
        logger.debug('Added prefixlength %s to the accumulator for address %s',
                     prefixlength, item.oid)
    # Types
    logger.debug('Address types')
    for item in snmp_walk(engine, auth, target, 'IP-MIB', 'ipAddressType', logger):
        acc[item.oid]['type'] = item.value
        logger.debug('Added type %s to the accumulator for address %s', item.value, item.oid)
    # Build the return structure
    result = {}
    for addr, details in acc.items():
        logger.debug('Examining address %s for the address map, with details %s', addr, details)
        # Is this the kind of address we want?
        if details['type'] != 'unicast':
            logger.debug('Rejecting non-unicast address %s with type %s',
                         addr, details['type'])
        # Build the interface object
        # Which IP version?
        if details['protocol'] == 'ipv4':
            address = ipaddress.IPv4Interface('%s/%s' % (details['address'],
                                                         details['prefixlength']))
        else:
            address = ipaddress.IPv6Interface('%s/%s' % (details['address'],
                                                         details['prefixlength']))
        logger.debug('Inferred address %s', address)
        if details['index'] not in result:
            result[details['index']] = []
        result[details['index']].append(address)
    # Return it
    logger.debug('Returning interface address map: %s', result)
    return result

def discover_host_networking(engine, auth, target, logger):
    '''
    Extract the device's network details, and return them as a nested structure:
    - interfaces
        - <SNMP index>
            - ifName    # Short name of the interface, in contrast to ifDescr
            - ifDescr   # Detailed text description of the interface
            - ifAlias   # Description string as configured by an administrator for this interface.
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
    # The following entries will be None if ifStackTable is not implemented on the target device.
    # They're explicitly set this way to make it simpler for client code to test for them.
    - ifStackTable      # Contents of the ifStackTable SNMP table
    '''
    logger.info('Discovering network details for host %s', target.transportAddr[0])
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
        for item in snmp_walk(engine, auth, target, 'IF-MIB', row, logger):
            if item.oid not in network['interfaces']:
                network['interfaces'][item.oid] = {}
            network['interfaces'][item.oid][row] = item.value
    logger.debug('Interfaces discovered:\n%s',
                 json.dumps(network['interfaces'], indent=4, sort_keys=True))
    # Map addresses to interfaces
    logger.debug('Mapping addresses to interfaces')
    network['ipIfaceAddrMap'] = get_iface_addr_map(engine, auth, target, logger)
    # ifStackTable encodes the relationship between subinterfaces and their parents.
    stack = get_if_stack_table(engine, auth, target, logger)
    if stack:
        network['ifStackTable'] = get_inv_stack_table(stack)
    else:
        network['ifStackTable'] = None
    # Return all the stuff we discovered
    return network

def explore_device(hostname, logger=None, community='public', port=161):
    '''
    Build up a picture of a device via SNMP queries.
    Return the results as a nest of dicts:
    - sysinfo: output of identify_host()
    - network: output of discover_host_networking()
    '''
    # Ensure we have a logger
    if not logger:
        logger = create_logger()
    # Dict to hold the device's information
    device = {}
    # Create SNMP engine
    snmpengine = pysnmp.hlapi.SnmpEngine()
    # Create auth creds
    snmpauth = pysnmp.hlapi.CommunityData(community, community)
    # Create transport target object
    snmptarget = pysnmp.hlapi.UdpTransportTarget((hostname, port))
    # Now get to work
    logger.info('Performing discovery on %s', hostname)
    # Top-level system information
    sysinfo = identify_host(snmpengine, snmpauth, snmptarget, logger)
    if sysinfo:
        device['sysinfo'] = sysinfo
        logger.debug('Discovered system information:\n%s',
                     json.dumps(device['sysinfo'], indent=4, sort_keys=True))
    else:
        logger.critical('Failed to gather even basic system information about %s', hostname)
        sys.exit(1)
    # Interfaces
    device['network'] = discover_host_networking(snmpengine, snmpauth, snmptarget, logger)
    # Return the information we found
    return device
