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
import paramiko
import traceback
from threading import Thread
import subprocess
import queue as queue
from zipfile import ZipFile, ZIP_DEFLATED

regionalData = {
                '1':{
                     'nacName':'NAC_NA',
                     'nacPrimary':'192.168.1.1',
                     'nacSecondary':'10.10.1.1',
                     'nacTertiary':'172.25.21.4',
                     'nacPrimaryName':'NAC-NA',
                     'nacSecondaryName':'NAC-AP',
                     'nacTertiaryName':'NAC-EAME'
                    },
                '2':{
                     'nacName':'NAC_EAME',
                     'nacPrimary':'172.25.1.1',
                     'nacSecondary':'192.168.1.1',
                     'nacTertiary':'10.10.1.1',
                     'nacPrimaryName':'NAC-EAME',
                     'nacSecondaryName':'NAC-NA',
                     'nacTertiaryName':'NAC-AP'
                    },
                '3':{
                     'nacName':'NAC_AP',
                     'nacPrimary':'10.159.217.5',
                     'nacSecondary':'172.25.1.1',
                     'nacTertiary':'192.168.1.1',
                     'nacPrimaryName':'NAC-AP',
                     'nacSecondaryName':'NAC-EAME',
                     'nacTertiaryName':'NAC-NA'
                    }
               }
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
    #config_txt = sys.argv[1]
    #os_version = sys.argv[2]
    #access_vlan = sys.argv[3]
    #voice_vlan = sys.argv[4]
    #authfail_vlan = sys.argv[5]
    config_txt = open(config_txt,'r').read()
    # Random Generated Output File
    outputDirectory = ''
    outputFileName = ''
    for i in range(6):
        outputDirectory += chr(random.randint(97,122))
    outputDirectory += '/'
    if not os.path.exists(outputDirectory):
        os.makedirs(outputDirectory)
    for i in range(6):
        outputFileName += chr(random.randint(97,122))
    outputFileName += '.txt'

    ## Create File Named For Device
    #outputFileName = outputDirectory +'/'+ device +'.txt'

    try:

        # Connection Break
        print(('*'*95))
        #counter = len(devices)-deviceList.qsize()
        #print(('['+str(counter)+'] Connecting to: '+device))
        #outputList.put(('['+str(counter)+'] Connecting to: '+device+'\n'))
        ## STDOUT BufferedIOBase
        #STDOUT = io.BufferedWriter(sys.stdout)
        # Connection Handler
        #connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=8)#,session_log=STDOUT) # NOT WORKING # #Enable Session_Log ONLY for troubleshooting on Acceptance

        mgmt_dict = {}
        mgmt_dict["trunks"]= []
        mgmt_dict["dot1x_ints"]= []
        mgmt_dict.update({"region": regionalData['1']})
        aaagroup = None

        ## Find OS Version
        #os_version = connection.send_command('show version | in RELEASE').strip().splitlines()[0].split('Version')[-1].strip().split()[0].strip(',')
        os_family = getOSFamilyIOS(os_version)
        mgmt_dict.update({"version": os_family})

        # Check for Trunks and configure DHCP Snooping Trust
        templist = []
        #output = connection.send_command('show lldp neighbors | in LAN|WAN').strip().splitlines()
        #for line in output:
        #    if (re.findall(u'[F|G|T][a|i|e][0-9][0-9]?\/[0-9][0-9]?\/?[0-9]?[0-9]?',line)):
        #        # Returns a list of all Regex matches, and we append index 0 to the list
        #        templist.append(re.findall(u'[F|G|T][a|i|e][0-9][0-9]?\/[0-9][0-9]?\/?[0-9]?[0-9]?',line)[0])
        templist = re.findall(u'interface (\w*(/\d){1,})(\n .*){0,}(switchport mode trunk)',config_txt)  
        for item in templist:
            mgmt_dict['trunks'].append(item[0])

        #output = connection.send_command('show interface trunk | begin spanning tree forwarding').strip().splitlines()
        #if len(output) > 1:
        #    for line in output[1:]:
        #        item = line.split()[0]
        #        if re.match(u'Po[0-9][0-9]?[0-9]?',item):
        #            members = connection.send_command('show interfaces '+ item +' | in Members').split('channel:')[1].split()
        #            for temp_item in members:
        #                if temp_item in templist:
        #                    mgmt_dict['trunks'].append(item)
        #        elif re.match(u'[F|G|T][a|i|e][0-9][0-9]?\/[0-9][0-9]?\/?[0-9]?[0-9]?',item):
        #            if item in templist:
        #                mgmt_dict['trunks'].append(item)



        ## Discover the VLANs and Cancel deployment if USER VLAN Name missing
        #access_vlan = ''
        #voice_vlan = ''
        #auth_fail_vlan = ''
        #output = connection.send_command('show vlan brief | in active').strip().splitlines()
        #for line in output:
        #    line = line.strip().split()
        #    if 'user_vlan' in line[1]:
        #        access_vlan = line[0]
        #    elif 'voice_1_vlan' in line[1]:
        #        voice_vlan = line[0]
        #    elif 'voice_2_vlan' in line[1]:
        #        voice_vlan = line[0]
        #    elif 'voice_3_vlan' in line[1]:
        #        voice_vlan = line[0]
        #    elif 'voice_4_vlan in line[1]:
        #        voice_vlan = line[0]
        #    elif 'voice_5_vlan' in line[1]:
        #        voice_vlan = line[0]
        #    elif 'authfail_vlan' in line[1]:
        #        auth_fail_vlan = line[0]

        # Append USER VLAN to Dict or Cancel deployment if USER VLAN Name missing
        mgmt_dict.update({'access_vlan': access_vlan})
        #if len(access_vlan) > 1:
        #    mgmt_dict.update({'access_vlan': access_vlan})
        #else:
        #    mgmt_dict.update({'access_vlan': access_vlan})
        #    outputList.put('['+str(counter)+'] VLANS: ********* WILL NOT DEPLOY DUE TO MISSING USER VLAN NAME **********\n')

        #    show_output = connection.send_command('show vlan brief | in active').strip().splitlines()
        #    outputList.put(('['+str(counter)+'] VLANS: ')+str('\n['+str(counter)+'] VLANS: ').join(show_output)+'\n')
        #    deploy = "No"


        # Append VOICE VLAN to Dict or Cancel deployment if VOICE VLAN name is missing
        mgmt_dict.update({'voice_vlan': voice_vlan})
        #if len(voice_vlan) > 1:
        #    mgmt_dict.update({'voice_vlan': voice_vlan})
        #else:
        #    mgmt_dict.update({'voice_vlan': voice_vlan})
        #    outputList.put('['+str(counter)+'] VLANS: ********* WILL NOT DEPLOY DUE TO MISSING VOICE VLAN NAME **********\n')

        #    show_output = connection.send_command('show vlan brief | in active').strip().splitlines()
        #    outputList.put(('['+str(counter)+'] VLANS: ')+str('\n['+str(counter)+'] VLANS: ').join(show_output)+'\n')
        #    deploy = "No"

        # Append Auth Fail VLAN to Dict
        mgmt_dict.update({'auth_fail_vlan': auth_fail_vlan})
        #if len(voice_vlan) > 1:
        #    mgmt_dict.update({'auth_fail_vlan': auth_fail_vlan})
        #else:
        #    mgmt_dict.update({'auth_fail_vlan': '88'})


        dot1x_interfaces = []
        int_voice_vlan = {}
        int_description = {}
        server_dead_vlan_dict = {}


        # Extract All interesting Interface configurations from running config
        #output = connection.send_command('show run')
        if not re.search(u'ip radius source-interface\s*(\S*)',config_txt):
            interface = re.search(u'ntp source\s*(\S*)',config_txt).group(1)
            mgmt_dict.update({"interface": interface})
        else:
            interface = re.search(u'ip radius source-interface\s*(\S*)',config_txt).group(1)
            mgmt_dict.update({"interface": interface})
        if re.search(u'ntp server vrf\s*(\S*)',config_txt):
            vrf = re.search(u'ntp server vrf\s*(\S*)',config_txt).group(1)
            mgmt_dict.update({"vrf": vrf})


        mgmt_int = None
        interface = None
        interfaceDescription = 'description 802.1x user port'
        interfaceVoiceVlan = mgmt_dict['voice_vlan']
        interfaceDict = {}
        for line in config_txt.splitlines():
            if line == 'interface '+mgmt_dict['interface']:
                mgmt_int = line
                print('MGMT_INTERFACE: !\n')
                print('MGMT_INTERFACE: '+line+'\n')
            elif line.lower().startswith('interface '):
                interface = line.split()[-1]
            elif line.strip() == '!':
                if interface is not None:
                    interfaceDict.update({interface:{'int_description':interfaceDescription,'int_voice_vlan':interfaceVoiceVlan}})
                if mgmt_int is not None:
                    print('MGMT_INTERFACE: !\n')
                mgmt_int = None
                interface = None
                interfaceDescription = 'description 802.1x user port'
                interfaceVoiceVlan = mgmt_dict['voice_vlan']
            elif interface is not None:
                if line.startswith(' description'):
                    interfaceDescription = line
                elif 'voice vlan' in line:
                    interfaceVoiceVlan = line
            elif mgmt_int is not None:
                print('MGMT_INTERFACE: '+line+'\n')



        ## Pull TACACS Group, and stop deployment if not using ISE
        #tacacsgroup=re.search(u'aaa authentication login default group\s*(\S*)',output)
        #if tacacsgroup and 'NDA' in tacacsgroup.group():
        #        mgmt_dict.update({"tacacsgroup": tacacsgroup.group(1)})
        #else:
        #    outputList.put('['+str(counter)+'] TACACS_GROUP: WILL NOT DEPLOY DUE TO LEGACY TACACS GROUP CONFIGURATIONS\n')
        #    outputList.put('['+str(counter)+'] TACACS_GROUP: '+show_output+'\n')
        #    deploy = "No"
        #    print('No Deploy')


        # Append All interesting Interface configurations
        mgmt_dict.update({'intInfo':interfaceDict})

        # Pull All Interfaces With Dot1x Enabled
        #output = connection.send_command('show dot1x all | include Info').replace('TenGigabitEthernet','Te').replace('GigabitEthernet','Gi').replace('FastEthernet','Fa').strip().splitlines()
        #for line in output:
        #    words = line.split()
        #    dot1x_interfaces.append(words[-1])
        templist = re.findall(u'interface (\w*(/\d+){1,})(\n .*){0,}(switchport access vlan (\d+))(\n .*){0,}(dot1x pae authenticator)',config_txt)  
        for item in templist:
            dot1x_interfaces.append(item[0])
            server_dead_vlan_dict.update({item[0]:item[4]})

        ## Pull Interface Dead VLAN
        #output = connection.send_command('sh interfaces status | in /').strip().splitlines()
        #for line in output:
        #    words = line.split()
        #    interface = words[0].replace('Gi','GigabitEthernet').replace('Te','TenGigabitEthernet').replace('Fa','FastEthernet')
        #    server_dead_vlan_dict.update({interface:words[-4]})

        # Update MGMT Dict with Dead VLAN for each interface
        for line in dot1x_interfaces:
            try:
                mgmt_dict['dot1x_ints'].append({'int_name': line,'server_dead_vlan': server_dead_vlan_dict[line],'int_description': int_description[line],'int_voice_vlan':int_voice_vlan[line]})
            except KeyError:
                mgmt_dict['dot1x_ints'].append({'int_name': line,'server_dead_vlan': mgmt_dict['access_vlan'],'int_description': ' description 802.1x User port','int_voice_vlan':mgmt_dict['voice_vlan'] })


        ## Test Print
        #pprint (mgmt_dict)
        #print '\n'.join(show_output)
        if os_family == '16':
            templateFileName = 'templates/IOS_16_3_5_NAC_config.j2'
        elif os_family == '03.08':
            templateFileName = 'templates/IOS_3_8_5_NAC_config.j2'
        else:
            templateFileName = 'templates/IOS_Other_NAC_config.j2'

        # Generataommand List using JINJA
        commandlist = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.BaseLoader).from_string(open(templateFileName,'r').read()).render(mgmt_dict)
        with open(outputFileName,'w') as outputFile:
            outputFile.write(commandlist)
        print(f'Config Output File: {outputFileName}')
        #if deploy == "yes":
        #    # Implement configuration Changes with SCP File Copy
        #    connection.send_config_set(['ip scp server enable'])
        #    scpConnection = netmiko.SCPConn(connection)
        #    scpConnection.scp_transfer_file(outputFileName,'ISEConfig.txt')
        #    connection.send_command_timing('copy run backup_config.txt')
        #    connection.send_command_timing('\n\n\n\n')
        #    time.sleep(10)
        #    connection.send_command_timing('  copy ISEConfig.txt run')
        #    connection.send_command_timing('\n\n\n')
        #    time.sleep(10)
        #    connection.send_command_timing('wr')
        #    connection.send_command_timing('\n\n\n')


        #    # Delete all extra templates and policies created during the IBNS2.0 conversion
        #    if os_family == '16' or os_family == '03.08':
        #        output = connection.send_command_timing('sh run | in service-template GUEST_VLAN\_.*|service-template AUTH_FAIL_VLAN\_.*|service-template GUEST_SUPP_VLAN\_.*|policy-map type control subscriber POLICY\_.*').strip().splitlines()
        #        extra_policies = ''
        #        for line in output:
        #            extra_policies += 'no '+ line +'\n'

        #        extraFileName = ''
        #        for i in range(6):
        #            extraFileName += chr(random.randint(97,122))
        #        extraFileName += '.txt'
        #        extraFileName = outputDirectory + extraFileName

        #        with open(extraFileName,'w') as outputFile:
        #            outputFile.write(extra_policies)
        #        scpConnection = netmiko.SCPConn(connection)
        #        scpConnection.scp_transfer_file(extraFileName,'extra_policies.txt')
        #        connection.send_command_timing('\n\n\n\n')
        #        connection.send_command_timing('copy extra_policies.txt run')
        #        connection.send_command_timing('\n\n\n')
        #        connection.send_command_timing('wr')
        #        connection.send_command_timing('\n\n\n')

        #        # DONT DELETE FILE HERE, ALL FILES ARE REMOVED AFTER ZIPPING
        #        #os.remove(extraFileName)


        ## Disconnect
        #connection.disconnect()
        ## DONT DELETE FILE HERE, ALL FILES ARE REMOVED AFTER ZIPPING
        ##os.remove(outputFileName)



    except Exception as e:    # exceptions as exceptionOccured:
        print('- CONFIGURATION ERROR:\n'+traceback.format_exc())
        # Print Full Exception
        print(traceback.format_exc())
    return
