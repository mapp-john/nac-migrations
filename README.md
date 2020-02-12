# nac-migrations

Main scripts are designed to be used in conjunction with a web app

# IBNS2.0 Only

Designed to be called as a function
NAC_CHANGE(config_txt,os_version,access_vlan,voice_vlan,auth_fail_vlan)

Example:
'''
>>> from CISCO_IOS_IBNS2 import NAC_CHANGE
>>> NAC_CHANGE('../Test/3850 sh run.txt','16.9.4','50','20','88')
***********************************************************************************************
***********************************************************************************************
Config Output File: livdto.txt
***********************************************************************************************
>>> 
'''
