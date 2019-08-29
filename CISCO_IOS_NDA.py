import os
import re
import time
import jinja2
import socket
import random
import logging
import netmiko
import paramiko
import threading
import subprocess
import queue as queue
from pprint import pprint
from EmailModule import emailHTMLWithRenamedAttachment


def NDA_CHANGE(username,password,counter,config,deploy,device_type,devices,deviceList,outputList,region):
    while not deviceList.empty():
        device = deviceList.get_nowait()
        try:

            # Connection Break
            print(('*'*95))
            counter = len(devices)-deviceList.qsize()
            print(('['+str(counter)+'] Connecting to: '+device))
            # Connection Handler
            connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=5)

            # Show Run for backup config
            outputList.put('\n['+str(counter)+'] Connecting to: '+device+'\n')
            show_run = connection.send_command('show run | in aaa').splitlines()
            outputList.put(('\n['+str(counter)+'] BACKUP_CONFIG: ')+str('\n['+str(counter)+'] BACKUP_CONFIG: ').join(show_run))
            show_run = connection.send_command('show run | in tacacs').splitlines()
            outputList.put(('\n['+str(counter)+'] BACKUP_CONFIG: ')+str('\n['+str(counter)+'] BACKUP_CONFIG: ').join(show_run))

            mgmt_dict = {}
            mgmt_dict["servers"]= []
            mgmt_dict.update({"region": int(region)})
            aaagroup = None

            # Show Command For version and MGMT config
            show_output= connection.send_command_timing('show run | in ntp|tacacs').splitlines()
            for line in show_output:
                if "ntp source " in line.lower():
                    interface = line.strip().split()[-1]
                    mgmt_dict.update({"interface": interface})

                elif "ip tacacs source-interface " in line.lower():
                    interface = line.strip().split()[-1]
                    mgmt_dict.update({"interface": interface})

                elif "ntp server vrf" in line.lower():
                    vrf = line.strip().split()[3]
                    mgmt_dict.update({"vrf": vrf})

                elif "aaa group server tacacs+" in line.lower():
                    aaagroup = line.strip().split()[-1]
                    if aaagroup.lower() not in ("pki-aaa", "nda_na", "nda_eame", "nda_ap"):
                        mgmt_dict.update({"aaagroup": aaagroup})

                elif "tacacs-server" in line:
                    if "host" in line:
                        server = line.strip().split()[-1]
                        mgmt_dict["servers"].append( server )
                    elif "key" in line:
                        old_key = line
                        mgmt_dict.update({"old_key": old_key })

            # Show Interface for backup config
            show_run = connection.send_command('show run interface ' + interface ).splitlines()
            outputList.put(('\n['+str(counter)+'] BACKUP_CONFIG: ')+str('\n['+str(counter)+'] BACKUP_CONFIG: ').join(show_run))

            show_output= connection.send_command_timing('show run | in radius')
            if "aaa accounting system default start-stop " in show_output.lower():
                mgmt_dict.update({"radiusgroups": "radius"})

            #elif "aaa group server radius " in show_output.lower():
            #    show_output= connection.send_command_timing('show run | in aaa group server radius')
            #    for line in show_output:
            #        radiusgroups = line.strip().replace("aaa group server radius","")
            #        mgmt_dict.update({"radiusgroups": str(radiusgroups)})

            elif "aaa group server radius " in show_output.lower():
                show_output= connection.send_command_timing('show run | in start-stop broadcast').splitlines()
                for line in show_output:
                    if "vrf" in line.lower() and aaagroup != None and 'tacvrf' not in line.lower():
                        radiusgroups = line.strip().replace("aaa accounting system default","").replace("vrf "+vrf,"").replace("start-stop broadcast group ","").replace("group tacacs+","").replace("group "+aaagroup,"")
                    elif aaagroup != None:
                        radiusgroups = line.strip().replace("aaa accounting system default","").replace("start-stop broadcast group ","").replace("group tacacs+","").replace("group "+aaagroup,"")
                    else:
                        radiusgroups = line.strip().replace("aaa accounting system default","").replace("start-stop broadcast group ","").replace("group tacacs+","")
                    mgmt_dict.update({"radiusgroups": str(radiusgroups)})


            show_output= connection.send_command_timing('sh ver | in Cisco IOS Software').splitlines()
            for line in show_output:
                if "version 16." in line.lower():
                    version = "16"
                    mgmt_dict.update({"version": str(version)})

            show_output= connection.send_command_timing('sh run | in aaa').splitlines()
            for line in show_output:
                if "aaa authorization commands 7" in line.lower():
                    commandseven = "7"
                    mgmt_dict.update({"commandseven": str(commandseven)})
                elif "aaa authorization commands 0" in line.lower():
                    commandszero = "0"
                    mgmt_dict.update({"commandszero": str(commandszero)})
                elif "aaa authorization commands 1" in line.lower():
                    commandsone = "1"
                    mgmt_dict.update({"commandsone": str(commandsone)})
                elif "aaa accounting commands 0" in line.lower():
                    commandszero = "0"
                    mgmt_dict.update({"commandszero": str(commandszero)})
                elif "aaa accounting commands 1" in line.lower():
                    commandsone = "1"
                    mgmt_dict.update({"commandsone": str(commandsone)})
                elif "authorization exec TACVRF" in line.lower():
                    tacvrf = "tacvrf"
                    mgmt_dict.update({"tacvrf": str(tacvrf)})

            ## Test Print
            #pprint (mgmt_dict)
            #print '\n'.join(show_output)

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
                    # Remove Local Admin
                    try:
                        # Connect to devices in list
                        conn_verify = netmiko.ConnectHandler(ip=device, device_type=device_type, username=username, password=password,global_delay_factor=4)
                        conn_verify.config_mode()
                        conn_verify.send_command_timing('no user ndaadmin')
                        conn_verify.send_command_timing('\n')
                        conn_verify.send_command_timing('end')
                        conn_verify.send_command_timing('wr')
                        outputList.put('\n['+str(counter)+'] Authentication Verified for '+device)
                        conn_verify.disconnect()
                    except:
                        outputList.put('\n['+str(counter)+'] '+device+'- Authentication Verification Failure\n'+cli_output)
            connection.disconnect()

        except:    # exceptions as exceptionOccured:
            outputList.put('\n['+str(counter)+'] '+device+'- TACACS Configuration Error\n')
    outputList.put(None)
    return

def script(form,dummyarg):

    # Pull variables from web form
    devices = form['devices'].strip().splitlines()
    username = form['username']
    password = form['password']
    email = form['email']
    region = form['region']
    deploy = form['deploy']

    # Netmiko Device Type
    device_type = 'cisco_ios'

    config=open('templates/IOS_NDA_config.j2','r').read()
	
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
        Thread(target=NDA_CHANGE, args=(username,password,counter,config,deploy,device_type,devices,deviceList,outputList,region)).start()
        time.sleep(1)

    with open(outputFileName,'w') as outputFile:
        numDone = 0
        while numDone < NUM_THREADS:
            result = outputList.get()
            if result is None:
                numDone += 1
            else:
                outputFile.write(result)

	
	
    ##############################
    # Email Out Result
    #
    subject = 'Results for IOS NDA Changes'
    html = """
    <html>
    <body>
    <h1>Output from Cisco IOS NDA Script</h1>
    </body>
    </html>
    """
    attachmentfile = ZipFileName
    attachmentname = 'Cisco_IOS_NDA.zip'
    #
    From = 'NAC Migration <NAC_Migration@domain.com>'
    #
    emailHTMLWithRenamedAttachment(email,subject,html,attachmentfile,attachmentname,From)

    # Delete Directory and Output File
    if os.path.exists(outputDirectory):
        shutil.rmtree(outputDirectory,ignore_errors=True)
    return
