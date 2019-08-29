import os
import re
import time
import jinja2
import socket
import random
import logging
import netmiko
import paramiko
from threading import Thread
import subprocess
import queue as queue
from pprint import pprint
from EmailModule import emailHTMLWithRenamedAttachment


def NDA_CHANGE(username,password,counter,config,deploy,device_type,deviceList,outputList,devices,region):
    while not deviceList.empty():
        device = deviceList.get_nowait()

        try:

            # Connection Break
            counter = len(devices)-deviceList.qsize()
            outputList.put('\n['+str(counter)+'] Connecting to: '+device)
            # Connection Handler
            connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=4)

            # Show Command For TACACS for backup
            show_output= connection.send_command_timing('show tacacs summary').splitlines()
            outputList.put(('\n['+str(counter)+'] BACKUP_CONFIG: ')+str('\n['+str(counter)+'] BACKUP_CONFIG: ').join(show_output))

            mgmt_dict = {}
            mgmt_dict.update({"region": int(region)})

            # Generataommand List using JINJA
            commandlist = jinja2.Environment(trim_blocks=True, lstrip_blocks=True).from_string(config).render(mgmt_dict).splitlines()

            ## Temp Print to verify
            #print '\n'.join(commandlist)

            # Generataommand List using JINJA
            commandlist = jinja2.Environment(trim_blocks=True, lstrip_blocks=True).from_string(config).render(mgmt_dict).splitlines()

            # Print CommandList to Output File
            outputList.put(('\n['+str(counter)+'] CONFIGURATION: ')+str('\n['+str(counter)+'] CONFIGURATION: ').join(commandlist))
            #for line in commandlist:
            #    outputList.put('\n['+str(counter)+'] CONFIGURATION: '+line)

            if deploy == "yes":
                # Implement configuration Changes with CommandList
                cli_output = connection.send_config_set(commandlist)

                # Create Exception for Command Auth Failure
                if cli_output.__contains__("Command authorization failed"):
                    raise Exception("Command authorization failed.")
                else:
                    outputList.put('['+str(counter)+'] Configuration Completed for '+device)
                    # Remove Local Admin
                    try:
                        # Connect to devices in list
                        outputList.put('['+str(counter)+'] Testing authentication and removing Local Admin on '+device)
                        conn_verify = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=4)
                        conn_verify.send_command('config mgmtuser delete ndaadmin')
                        conn_verify.send_command_timing('save config')
                        conn_verify.send_command_timing('y')
                        outputList.put('\n['+str(counter)+'] Authentication Verified for '+device)
                        conn_verify.disconnect()
                    except:
                        outputList.put('\n['+str(counter)+'] '+device+' - Authentication Verification Failure')
            connection.disconnect()
                # Create Exception for Command Auth Failure

        except Exception as exception:    # exceptions as exceptionOccured:
            outputList.put('\n['+str(counter)+'] '+device+'- TACACS Configuration Error\n')
    outputList.put(None)
    return

def script(form,dummyarg):

    # Pull variables from web form
    devices = form['devices'].strip().splitlines()
    username = form['username']
    password = form['password']
    email = form['email']
    deploy = form['deploy']
    region = form['region']

    # Netmiko Device Type
    device_type='cisco_wlc'

    # Common exceptions that could cause issues
    exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                  netmiko.ssh_exception.NetMikoAuthenticationException)


    config=open('templates/WLC_NDA_config.j2','r').read()


    # Define Threading Queues
    NUM_THREADS = 20
    deviceList = queue.Queue()
    outputList = queue.Queue()

    if len(devices) < NUM_THREADS:
        NUM_THREADS = len(devices)
    for line in devices:
        deviceList.put(line.strip())

    # Random Generated Output File
    outputDirectory = 'tmp/'
    outputFileName = ''
    for i in range(6):
        outputDirectory += chr(random.randint(97,122))
    outputDirectory += '/'
    if not os.path.exists(outputDirectory):
        os.makedirs(outputDirectory)
    for i in range(6):
        outputFileName += chr(random.randint(97,122))
    outputFileName += '.txt'
    outputFileName = outputDirectory+outputFileName

    counter = 0

    # loop for devices
    for i in range(NUM_THREADS):
        Thread(target=NDA_CHANGE, args=(username,password,counter,config,deploy,device_type,deviceList,outputList,devices,region)).start()
        time.sleep(1)


    with open(outputFileName,'w') as outputFile:
        numDone = 0
        while numDone < NUM_THREADS:
            result = outputList.get()
            if result is None:
                numDone += 1
            else:
                outputFile.write(result)

    # Send Email With Results Attached
    subject = 'Results for WLC NDA Changes'
    html = """
    <html>
    <body>
    <h1>Output from WLC NDA Changes</h1>
    </body>
    </html>
    """
    attachmentfile = outputFileName
    attachmentname = 'results.csv'
    #
    From = 'NAC Migration <NAC_Migration@domain.com>'
    #
    emailHTMLWithRenamedAttachment(email,subject,html,attachmentfile,attachmentname,From)
    os.remove(outputFileName)
    return
