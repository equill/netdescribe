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

# Included batteries
from collections import namedtuple
import re


# Data structures
SnmpDatum = namedtuple('snmpDatum', ['oid', 'value'])
IpAddress = namedtuple('ipAddress', ['address', 'netmask'])


# Utility functions

def snmp_get(hostname, mib, attr, community, logger, port=161):
    '''
    Perform an SNMP GET for a single OID or scalar attribute.
    Return only the value.
    '''
    # Use pysnmp to retrieve the data
    error_indication, error_status, error_index, var_binds = next(
        pysnmp.hlapi.getCmd(pysnmp.hlapi.SnmpEngine(), # Create the SNMP engine
                            # Authentication: set the SNMP version (2c)
                            # and community-string
                            pysnmp.hlapi.CommunityData(community, mpModel=1),
                            # Set the transport and target: UDP, hostname:port
                            pysnmp.hlapi.UdpTransportTarget((hostname, port)),
                            # Context is a v3 thing, but appears to be required anyway
                            pysnmp.hlapi.ContextData(),
                            # Specify the MIB object to read.
                            # The 0 means we're retrieving a scalar value.
                            pysnmp.hlapi.ObjectType(pysnmp.hlapi.ObjectIdentity(mib, attr, 0))))
    # Handle the responses
    if error_indication:
        logger.error(error_indication)
        return False
    elif error_status:
        logger.error('%s at %s' % (error_status.prettyPrint(),
                                   error_index and var_binds[int(error_index) - 1][0] or '?'))
        return False
    # If we actually got something, return it as an SnmpDatum
    else:
        return var_binds[0][1].prettyPrint()

def snmp_bulk_get(hostname, mib, attr, community, logger, port=161):
    '''
    Perform an SNMP BULKGET on mib::attr.
    Return a dict:
    - rowname
        - list of SnmpDatum namedTuples
    This structure mirrors SNMP's representation of tables as rows with indexed values.
    '''
    logger.debug('Querying %s for %s::%s', hostname, mib, attr)
    # Number of nonrepeating MIB variables in the request
    non_repeaters = 0
    # Maximum number of variables requested for each of the remaining MIB variables in the request
    max_repetitions = 10000
    # Use pysnmp to retrieve the data
    data = {} # Accumulator for the results
    engine = pysnmp.hlapi.bulkCmd(pysnmp.hlapi.SnmpEngine(),
                                  # Create the SNMP engine
                                  # Authentication: set the SNMP version (2c)
                                  # and community-string
                                  pysnmp.hlapi.CommunityData(community, mpModel=1),
                                  # Set the transport and target: UDP, hostname:port
                                  pysnmp.hlapi.UdpTransportTarget((hostname, port)),
                                  # Context is a v3 thing, but is required anyway
                                  pysnmp.hlapi.ContextData(),
                                  ## Specify operational limits
                                  non_repeaters,
                                  max_repetitions,
                                  # Specify the MIB object to read.
                                  pysnmp.hlapi.ObjectType(pysnmp.hlapi.ObjectIdentity(mib, attr)),
                                  # Stop when we get results outside the scope we
                                  # requested, instead of carrying on until the agent runs
                                  # out of OIDs to send back.
                                  lexicographicMode=False,
                                  # Convert
                                  lookupMib=True)
    for error_indication, error_status, error_index, var_binds in engine:
        # Handle the responses
        if error_indication:
            logger.error(error_indication)
            return False
        elif error_status:
            logger.error('%s at %s' % (error_status.prettyPrint(),
                                       error_index and var_binds[int(error_index) - 1][0] or '?'))
            return False
        # If we actually got something, return it in human-readable form
        else:
            for var_bind in var_binds:
                # Extract the index values.
                # We're breaking down 'IF-MIB::ifType.530' into (row='ifType', index='530').
                # This relies on 'lookupMib=True', to translate numeric OIDs into textual ones.
                keys = re.split('\.', re.split('::', var_bind[0].prettyPrint())[1], maxsplit=1)
                row = keys[0]
                index = keys[1]
                # Now get the value
                val = var_bind[1].prettyPrint()
                # Update the results table, ensuring the row is actually present
                logger.debug('%s.%s = %s', row, index, val)
                if row not in data:
                    data[row] = []
                data[row].append(SnmpDatum(oid=index, value=val))
    # Return what we found
    return data


# Functions to actually get the data

def identify_host(hostname, logger, community='public'):
    '''
    Extract some general identifying characteristics.
    Return a dict:
    - sysName       # Hostname. Should be the FDQN, but don't count on it.
    - sysDescr      # Detailed text description of the system.
    - sysObjectID   # Vendor's OID identifying the device.
    - sysServices   # Network-layer services offered by this device.
                    # Uses weird maths, but may be usable.
    '''
    logger.debug('Querying %s for general details', hostname)
    data = {}
    for attr in ['sysName',
                 'sysDescr',
                 'sysObjectID',
                 'sysServices',]:
        response = snmp_get(hostname, 'SNMPv2-MIB', attr, community, logger)
        if response:
            data[attr] = response
    return data

def get_if_stack_table(hostname, community, logger):
    '''
    Extract IF-MIB::ifStackTable from a device, per
    http://www.net-snmp.org/docs/mibs/ifMIBObjects.html
    and return it as a dict, where the key is the higher layer, and
    the value is the lower.
    '''
    logger.debug('Attempting to query %s for ifStackTable', hostname)
    data = {}
    rawdata = snmp_bulk_get(hostname, 'IF-MIB', 'ifStackTable', community, logger)
    logger.debug('rawdata: %s', rawdata)
    for datum in rawdata['ifStackStatus']:
        logger.debug("Entry: %s" % datum.oid)
        stackparts = re.split('\.', datum.oid)
        upper = stackparts[0]
        lower = stackparts[1]
        logger.debug("Upper: %s. Lower: %s." % (upper, lower))
        data[upper] = lower
    logger.debug('ifStackTable: %s', data)
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

def if_inv_stack_table_to_nest(table, index='0'):
    '''
    Take a table as output by the first section of get_inv_stack_table().
    Return a recursively nested dict:
    - key = SNMP index of an interface
    - value = False if this interface has no subinterfaces.
              If it _does_ have subinterfaces, a dict whose keys are their indices
    '''
    # If the value for this index is 0, this interface has no subinterfaces.
    # Return False to indicate this.
    if table[index] == '0':
        return False
    # Otherwise, there are subinterfaces to enumerate.
    # Recurse through this function.
    else:
        acc = {}
        for sub in table[index]:
            acc[sub] = if_inv_stack_table_to_nest(table, sub)
        return acc

def get_iface_addr_map(hostname, community, logger):
    '''
    Extract a mapping of addresses to interfaces.
    Return a structure contained in a parent dict:
    - interface index (for reconciling with other interface data)
        - list of IpAddress namedtuples
    Tested only on Juniper SRX100 so far.
    '''
    addr_index = snmp_bulk_get(hostname,
                               'IP-MIB',
                               'ipAdEntIfIndex',
                               community,
                               logger)['ipAdEntIfIndex']
    addr_netmask = snmp_bulk_get(hostname,
                                 'IP-MIB',
                                 'ipAdEntNetMask',
                                 community,
                                 logger)['ipAdEntNetMask']
    # SNMP returns this to us by address not interface.
    # Thus, we have to build an address-oriented dict first, then assemble the final result.
    acc = {}    # Intermediate accumulator for building up a map
    # Addresses
    for item in addr_index.items():
        acc[item.name] = {'index': item.value}
    # Netmasks
    for item in addr_netmask.items():
        acc[item.name]['netmask'] = item.value
    # Build the return structure
    result = {}
    for addr, details in acc.items():
        # Ensure there's an entry for this interface
        if details['index'] not in result:
            result[details['index']] = []
        result[details['index']].append(IpAddress(address=addr, netmask=details['netmask']))
    # Return it
    return result

def iface_addr_map_to_dicts(imap):
    '''
    Convert the output of get_iface_addr_map() to a nest of dicts,
    for returning by discover_network().
    Return structure is as follows:
    - interface index (relative to ifTable)
        - list of dicts:
            - address = IP address for interface
            - netmask = netmask for interface address
    '''
    result = {}
    for iface, addrlist in imap.items():
        result[iface] = [{'address': addr.address, 'netmask': addr.netmask} for addr in addrlist]
    return result

def discover_host_networking(hostname, community, logger):
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
    - ifIfaceAddrMap      # Mapping of addresses to interface indices
        - interface index (relative to ifTable)
            - list of dicts:
                - address = IP address for interface
                - netmask = netmask for interface address
    # The following entries will be None if ifStackTable is not implemented on the target device.
    # They're explicitly set this way to make it simpler for client code to test for them.
    - ifStackTable      # Contents of the ifStackTable SNMP table
    - ifStackTree       # Mapping of parent interfaces to subinterfaces from StackToDict()
    '''
    network = {'interfaces': {}}
    # Basic interface details
    if_table = snmp_bulk_get(hostname, 'IF-MIB', 'ifTable', community, logger)
    for row in ['ifDescr',
                'ifType',
                'ifSpeed',
                'ifPhysAddress']:
        for item in if_table[row].items():
            if item.oid not in network['interfaces']:
                network['interfaces'][item.oid] = {}
            network['interfaces'][item.oid][row] = item.value
    # Extended interface details
    ifxtable = snmp_bulk_get(hostname, 'IF-MIB', 'ifXTable', community, logger)
    for row in ['ifName',
                'ifHighSpeed',
                'ifAlias']:
        for item in ifxtable[row].items():
            network['interfaces'][item.oid][row] = item.value
    # Map addresses to interfaces
    network['ifIfaceAddrMap'] = iface_addr_map_to_dicts(
        get_iface_addr_map(hostname, community, logger))
    # ifStackTable encodes the relationship between subinterfaces and their parents.
    stack = get_if_stack_table(hostname, community, logger)
    if stack:
        network['ifStackTable'] = get_inv_stack_table(stack)
        network['ifStackTree'] = if_inv_stack_table_to_nest(network['ifStackTable'])
    else:
        network['ifStackTable'] = None
        network['ifStackTree'] = None
    # Return all the stuff we discovered
    return network

def explore_device(hostname, logger, community='public'):
    '''
    Build up a picture of a device via SNMP queries.
    Return the results as a nest of dicts:
    - sysinfo: output of identify_host()
    - network: output of discover_host_networking()
    '''
    logger.info('Performing discovery on %s', hostname)
    # Dict to hold the device's information
    device = {}
    # Top-level system information
    device['sysinfo'] = identify_host(hostname, logger, community)
    # Interfaces
    device['network'] = discover_host_networking(hostname, community, logger)
    # Return the information we found
    return device
