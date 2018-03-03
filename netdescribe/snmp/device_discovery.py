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
from netdescribe.snmp.snmp_functions import snmp_get, snmp_walk
from netdescribe.snmp.class_brocade import Brocade
from netdescribe.snmp.class_linux import Linux
from netdescribe.snmp.class_mib2 import Mib2

# Included modules
import re


# Functions to actually get the data

# Not yet fully usable.
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

# Not yet fully usable
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

def create_device(hostname, logger, community, port):
    '''
    Create and return an object representing the device to be discovered.
    Choose the most appropriate class, according to its sysObjectID.
    '''
    logger.info('Creating a device')
    # Create SNMP engine
    snmpengine = pysnmp.hlapi.SnmpEngine()
    # Create auth creds
    snmpauth = pysnmp.hlapi.CommunityData(community, community)
    # Create transport target object
    snmptarget = pysnmp.hlapi.UdpTransportTarget((hostname, port))
    # Get the sysObjectId for this device
    object_id = snmp_get(snmpengine,
                         snmpauth,
                         snmptarget,
                         'SNMPv2-MIB',
                         'sysObjectID',
                         logger)
    logger.debug('sysObjectID: {}'.format(object_id))
    # Create and return the object itself
    # Brocade
    if re.match(".*1991.*", object_id):
        logger.info('Detected Brocade, probably Ironware.')
        return Brocade(snmptarget, snmpengine, snmpauth, logger, sysObjectID=object_id)
    # Linux
    # For other OSes running NetSNMP, see http://www.oidview.com/mibs/8072/NET-SNMP-TC.html
    if re.match(".*8072.3.2.10", object_id):
        logger.info('Detected Linux.')
        return Linux(snmptarget, snmpengine, snmpauth, logger, sysObjectID=object_id)
    # Junos
    # For model specifics, see http://www.oidview.com/mibs/2636/JUNIPER-CHASSIS-DEFINES-MIB.html
    # The Mib2 class works well enough for now, but will need replacing when Juniper-specific
    # details are needed.
    if re.match(".*2636.1.1.1.*", object_id):
        logger.info('Detected Junos.')
        return Mib2(snmptarget, snmpengine, snmpauth, logger, sysObjectID=object_id)
    # Fall back to the default
    logger.info('Unrecognised sysObjectID for %s is %s. Creating a MIB-2 object',
                hostname, object_id)
    return Mib2(snmptarget, snmpengine, snmpauth, logger, sysObjectID=object_id)

def explore_device(hostname, logger=None, community='public', port=161):
    '''
    Build up a picture of a device via SNMP queries.
    Return the results as an instance of the class that best matches the detected
    SNMP implementation.
    '''
    # Ensure we have a logger
    if not logger:
        logger = create_logger()
    # Now get to work
    logger.info('Performing discovery on %s', hostname)
    # Create an object to represent this device,
    # taking its SNMP capabilities into account
    device = create_device(hostname, logger, community, port)
    # Perform discovery as appropriate to this device type
    device.discover()
    # Return the device object, complete with its discovered data
    return device
