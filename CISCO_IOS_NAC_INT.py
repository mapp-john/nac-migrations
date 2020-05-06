import os
import re
import time
import json
import shutil
import jinja2
import socket
import random
import logging
import netmiko
import paramiko
from threading import Thread
import queue
from zipfile import ZipFile, ZIP_DEFLATED
from EmailModule import emailHTMLWithRenamedAttachment

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


def NDA_CHANGE(username,password,counter,deploy,device_type,device,outputList,outputDirectory,interfaces):
    #while not deviceList.empty():
        #device = deviceList.get_nowait()

    # Create File Named For Device
    outputFileName = outputDirectory +'/'+ device +'.txt'

    try:

        # Connection Break
        print(('*'*95))
        #counter = len(devices)-deviceList.qsize()
        counter = 1
        print(('['+str(counter)+'] Connecting to: '+device))
        outputList.put(('['+str(counter)+'] Connecting to: '+device))
        # Connection Handler
        connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=5)

        mgmt_dict = {}
        mgmt_dict["dot1x_ints"]= []
        aaagroup = None

        # Find OS Version
        os_version = connection.send_command('show version | in RELEASE').strip().splitlines()[0].split('Version')[-1].strip().split()[0].strip(',')
        os_family = getOSFamilyIOS(os_version)
        mgmt_dict.update({"version": os_family})

        # Discover the VLANs and Cancel deployment if USER VLAN Name missing
        access_vlan = ''
        voice_vlan = ''
        auth_fail_vlan = ''
        output = connection.send_command('show vlan brief | in active').strip().splitlines()
        for line in output:
            line = line.strip().split()
            if 'user_vlan' in line[1]:
                access_vlan = line[0]
            elif 'voice_1_vlan' in line[1]:
                voice_vlan = line[0]
            elif 'voice_2_vlan' in line[1]:
                voice_vlan = line[0]
            elif 'voice_3_vlan' in line[1]:
                voice_vlan = line[0]
            elif 'voice_4_vlan in line[1]:
                voice_vlan = line[0]
            elif 'voice_5_vlan' in line[1]:
                voice_vlan = line[0]
            elif 'authfail_vlan' in line[1]:
                auth_fail_vlan = line[0]

        # Append USER VLAN to Dict or Cancel deployment if USER VLAN Name missing
        if len(access_vlan) > 1:
            mgmt_dict.update({'access_vlan': access_vlan})
        else:
            mgmt_dict.update({'access_vlan': access_vlan})
            outputList.put('['+str(counter)+'] VLANS: ********* WILL NOT DEPLOY DUE TO MISSING USER VLAN NAME **********\n')

            show_output = connection.send_command('show vlan brief | in active').strip().splitlines()
            outputList.put(('['+str(counter)+'] VLANS: ')+str('\n['+str(counter)+'] VLANS: ').join(show_output)+'\n')
            deploy = "No"


        # Append VOICE VLAN to Dict or Cancel deployment if VOICE VLAN name is missing
        if len(voice_vlan) > 1:
            mgmt_dict.update({'voice_vlan': voice_vlan})
        else:
            mgmt_dict.update({'voice_vlan': voice_vlan})
            outputList.put('['+str(counter)+'] VLANS: ********* WILL NOT DEPLOY DUE TO MISSING VOICE VLAN NAME **********\n')

            show_output = connection.send_command('show vlan brief | in active').strip().splitlines()
            outputList.put(('['+str(counter)+'] VLANS: ')+str('\n['+str(counter)+'] VLANS: ').join(show_output)+'\n')
            deploy = "No"

        # Append Auth Fail VLAN to Dict
        if len(voice_vlan) > 1:
            mgmt_dict.update({'auth_fail_vlan': auth_fail_vlan})
        else:
            mgmt_dict.update({'auth_fail_vlan': '88'})



        interfaces = interfaces.split(',')

        # Update MGMT Dict with Dead VLAN for each interface
        for line in interfaces:
            #line = line.replace('Gi','GigabitEthernet').replace('Te','TenGigabitEthernet').replace('Fa','FastEthernet')
            mgmt_dict['dot1x_ints'].append({'int_name': line.strip() })

        # Pull TACACS Group, and stop deployment if not using ISE
        show_output= connection.send_command_timing('show run | in aaa authentication dot1x').strip()
        if not "NAC_" in show_output:
            outputList.put('['+str(counter)+'] RADIUS_GROUP: WILL NOT DEPLOY DUE TO LEGACY RADIUS GROUP CONFIGURATIONS\n')
            outputList.put('['+str(counter)+'] RADIUS_GROUP: '+show_output+'\n')
            deploy = "No"


        ## Test Print
        #print (json.dumps(mgmt_dict,indent=4, sort_keys=True))
        #print '\n'.join(show_output)
        if os_family == '16':
            templateFileName = 'templates/IOS_16_3_5_NAC_INT_config.j2'
        elif os_family == '03.08':
            templateFileName = 'templates/IOS_3_8_5_NAC_INT_config.j2'
        else:
            templateFileName = 'templates/IOS_Other_NAC_INT_config.j2'

        # Generataommand List using JINJA
        commandlist = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.BaseLoader).from_string(open(templateFileName,'r').read()).render(mgmt_dict)
        with open(outputFileName,'w') as outputFile:
            outputFile.write(commandlist)
        ## TEST PRINT
        #for line in commandlist.splitlines(): print(line)

        if deploy == "yes":
            # Implement configuration Changes with SCP File Copy
            connection.send_config_set(['ip scp server enable'])
            scpConnection = netmiko.SCPConn(connection)
            scpConnection.scp_transfer_file(outputFileName,'ISE_INT_Config.txt')
            connection.send_command_timing('copy run backup_INT_config.txt')
            connection.send_command_timing('\n\n\n\n')
            time.sleep(10)
            connection.send_command_timing('  copy ISE_INT_Config.txt run')
            connection.send_command_timing('\n\n\n')
            time.sleep(10)
            connection.send_command_timing('wr')
            connection.send_command_timing('\n\n\n')

        # Disconnect
        connection.disconnect()
        # DONT DELETE FILE HERE, ALL FILES ARE REMOVED AFTER ZIPPING
        #os.remove(outputFileName)



    except Exception as e:    # exceptions as exceptionOccured:
        outputList.put('\n['+str(counter)+'] '+device+'- CONFIGURATION ERROR:\n'+traceback.format_exc())
        if connection: connection.disconnect()
        # Print Full Exception
        print(traceback.format_exc())
    outputList.put(None)
    return

def script(form,configSettings):

    # Pull variables from web form
    device = form['device']
    username = form['username']
    password = form['password']
    email = form['email']
    interfaces = form['interfaces']
    deploy = form['deploy']

    # Netmiko Device Type
    device_type = 'cisco_ios'



    # Define Threading Queues
    #NUM_THREADS = 20
    #deviceList = queue.Queue()
    outputList = queue.Queue()

    #if len(devices) < NUM_THREADS:
    #    NUM_THREADS = len(devices)
    #for line in devices:
    #    deviceList.put(line.strip())

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

    counter = 0

    # loop for devices
    #for i in range(NUM_THREADS):
    #    Thread(target=NDA_CHANGE, args=(username,password,counter,deploy,device_type,device,outputList,outputDirectory,interfaces)).start()
    #    time.sleep(1)
    NDA_CHANGE(username,password,counter,deploy,device_type,device,outputList,outputDirectory,interfaces)



    # Writes the output Queue to file
    with open(outputFileName,'w') as outputFile:
        numDone = 0
        while numDone < 1:
            result = outputList.get()
            if result is None:
                numDone += 1
            else:
                outputFile.write(result)


    # ZIP Directory of Output Files
    find = outputDirectory.rfind('/')
    ZipFileName = outputDirectory[:find] + '.zip'
    with ZipFile(ZipFileName, 'w', ZIP_DEFLATED) as zf:
        # Writes Output File file and renames file
        zf.write(outputFileName, 'results.csv')
        # Iterates through Directory
        for File in os.scandir(outputDirectory):
            if not File.name.startswith('.') and File.is_file():
                # Writes the file using the full file path + name
                zf.write(File.path, File.name)


    ##############################
    # Email Out Result
    #
    subject = 'Results for IOS NAC Interface Changes'
    html = """
    <html>
    <body>
    <h1>Output from Cisco IOS NAC Interface Script</h1>
    </body>
    </html>
    """
    attachmentfile = ZipFileName
    attachmentname = 'Cisco_IOS_NAC_INT.zip'
    #
    From = 'NAC Migration <NAC_Migration@domain.com>'
    #
    emailHTMLWithRenamedAttachment(email,subject,html,attachmentfile,attachmentname,From)

    # Delete Directory and Output File
    if os.path.exists(outputDirectory):
        shutil.rmtree(outputDirectory,ignore_errors=True)
    os.remove(ZipFileName)
    os.remove(outputFileName)

    return
