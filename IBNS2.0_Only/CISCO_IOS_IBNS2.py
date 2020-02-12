import io
import os
import re
import sys
import time
import shutil
import jinja2
import socket
import random
import logging
import netmiko
import traceback

def getOSFamilyIOS(os_version):
    if os_version.startswith('12.'):
        os_family = '12'
    elif os_version.startswith('15.'):
        os_family = '15'
    elif os_version.startswith('16.'):
        os_family = '16'
    elif os_version.startswith('03.'):
        os_family = '.'.join(os_version.split('.')[:2])
    else:
        os_family = ''
    return os_family


def NAC_CHANGE(config_txt,os_version,access_vlan,voice_vlan,auth_fail_vlan):
    config_txt = open(config_txt,'r').read()
    # Random Generated Output File
    outputFileName = ''
    for i in range(6):
        outputFileName += chr(random.randint(97,122))
    outputFileName += '.txt'

    try:

        # Connection Break
        print(('*'*95))
        mgmt_dict = {}
        mgmt_dict["trunks"]= []
        mgmt_dict["dot1x_ints"]= []

        # Find OS Version
        os_family = getOSFamilyIOS(os_version)
        mgmt_dict.update({"version": os_family})

        # Choose template
        if os_family == '16':
            templateFileName = 'templates/IOS_16_3_5_IBNS2.0.j2'
        elif os_family == '03.08':
            templateFileName = 'templates/IOS_3_8_5_IBNS2.0.j2'
        else:
            print(('*'*95))
            print('ERROR: Template Not Selected')
            return

        # Check for Trunks and configure DHCP Snooping Trust
        templist = re.findall(u'interface (\w*(/\d){1,})(\n .*){0,}(switchport mode trunk)',config_txt)
        for item in templist:
            mgmt_dict['trunks'].append(item[0])

        # Append USER VLAN to Dict or Cancel deployment if USER VLAN Name missing
        mgmt_dict.update({'access_vlan': access_vlan})
        # Append VOICE VLAN to Dict or Cancel deployment if VOICE VLAN name is missing
        mgmt_dict.update({'voice_vlan': voice_vlan})

        # Append Auth Fail VLAN to Dict
        mgmt_dict.update({'auth_fail_vlan': auth_fail_vlan})

        # Extract All interesting Interface configurations from running config
        dot1x_interfaces = []
        int_voice_vlan = {}
        int_description = {}
        server_dead_vlan_dict = {}

        mgmt_int = None
        interface = None
        interfaceDescription = 'description 802.1x user port'
        host_mode = 'multi-domain'
        auth_mode = 'closed'
        interfaceDict = {}

        # Pull All Interfaces With Dot1x Enabled and populate with default description/host-mode/auth-mode
        templist = re.findall(r'interface (\w*(\/\d+){1,})(\n .*){0,}(dot1x pae authenticator)',config_txt)
        if templist:
            for item in templist:
                dot1x_interfaces.append(item[0])
                interfaceDict.update({item[0]:{'int_name':item[0],'int_description':interfaceDescription,'host_mode':host_mode,'auth_mode':auth_mode}})
        else:
            print(('*'*95))
            print('ERROR: No Dot1x Interfaces Found')
            return

        # Search for interface descriptions
        templist = re.findall(r'interface (\w*(\/\d+){1,})(\n .*){0,}(description .*)(\n .*){0,}(dot1x pae authenticator)',config_txt)
        if templist:
            for item in templist:
                interfaceDict[item[0]]['int_description'] = item[3]
        # Search for open auth interfaces
        templist = re.findall(r'interface (\w*(\/\d+){1,})(\n .*){0,}(authentication (open))(\n .*){0,}(dot1x pae authenticator)',config_txt)
        if templist:
            for item in templist:
                interfaceDict[item[0]]['auth_mode'] = item[4]
        # Search for Multi-Auth interfaces
        templist = re.findall(r'interface (\w*(\/\d+){1,})(\n .*){0,}(\n .*){0,}(authentication host-mode (\w*-\w*))(\n .*){0,}(\n .*){0,}(dot1x pae authenticator)',config_txt)
        if templist:
            for item in templist:
                if item[5] in ['multi-domain','multi-auth']:
                    interfaceDict[item[0]]['host_mode'] = item[5]
        ## TEST PRINT
        #print(interfaceDict)

        # Update MGMT Dict with details for each interface
        for item in dot1x_interfaces:
            try:
                mgmt_dict['dot1x_ints'].append(interfaceDict[item])
            except KeyError:
                mgmt_dict['dot1x_ints'].append({'int_name': item,'int_description': interfaceDescription,'host_mode':host_mode,'auth_mode':auth_mode})

        ## TEST PRINT
        #print(mgmt_dict)

        # Generataommand List using JINJA
        commandlist = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.BaseLoader).from_string(open(templateFileName,'r').read()).render(mgmt_dict)
        with open(outputFileName,'w') as outputFile:
            outputFile.write(commandlist)
        print(('*'*95))
        print(f'Config Output File: {outputFileName}')
        print(('*'*95))

    except Exception as e:    # exceptions as exceptionOccured:
        print('CONFIGURATION ERROR:\n'+traceback.format_exc())
    return
