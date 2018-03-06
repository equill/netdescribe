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
General SNMP functions
"""

# Third-party libraries
import pysnmp.hlapi

# Built-in modules
from collections import namedtuple
import re


# Data structures
SnmpDatum = namedtuple('snmpDatum', ['oid', 'value'])


# Basic functions

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
    returnval = None
    if error_indication:
        logger.error(error_indication)
        raise RuntimeError(error_indication)
    elif error_status:
        logger.error('%s at %s' % (error_status.prettyPrint(),
                                   error_index and var_binds[int(error_index) - 1][0] or '?'))
        raise RuntimeError(error_status.prettyPrint())
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
