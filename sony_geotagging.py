#!/usr/bin/env python3

import os
import time
import sys
import argparse
import socket
import serial
from datetime import datetime

import subprocess
from _socket import timeout

# sudo -H pip3 install "pygatt[GATTTOOL]" timezonefinder pytz binascii

import binascii
from os import device_encoding
import pygatt
import logging
from timezonefinder import TimezoneFinder
import pytz
     
DEVICE = "48:EB:62:E3:71:12"
blueTryConnectTimes = 10

# logging.basicConfig()
# logging.getLogger('pygatt').setLevel(logging.DEBUG)


def myConnectionTest():
    """
    when the camera is off and still returns connection replies.
    So I'm able to read and write characteristics. All the characteristics, 
    have the same values, except from the "0000cc05-0000-1000-8000-00805f9b34fb". 
    When the camera is on, the characteristic  is 0400000000
    whereas when camera is off, is 0400000204.
    """
    global adapter
    global device
    try:
        temp = device.char_read("0000cc05-0000-1000-8000-00805f9b34fb")
        if(temp[-1] == 0):
            # print("Connected")
            return True
        else:
            # print("Not Connected")
            return False
    except:
        # print("Nothing")
        return False

        

def handle_data(handle, value):
    """
    handle -- integer, characteristic read handle the data was received on
    value -- bytearray, the data returned in the notification
    """
    print("Received data: %s" % binascii.hexlify(value))

def set_location(latitude,longitude):
    myLat = (int)(latitude * int(1e7))
    myLng = (int)(longitude * int(1e7))
    myLatByte = myLat.to_bytes(4, byteorder='big', signed=True )
    myLngByte = myLng.to_bytes(4, byteorder='big', signed=True )
    coordinates = myLatByte + myLngByte
    return coordinates

def set_date(tz):
    dateTimeObj = datetime.now(tz)
    yearBytes = dateTimeObj.year.to_bytes(2, byteorder='big')
    full_date =  bytearray([ 
        yearBytes[0], yearBytes[1], dateTimeObj.month, dateTimeObj.day,
        dateTimeObj.hour, dateTimeObj.minute, dateTimeObj.second
    ])
    return full_date

def sendToCamera(latitude, longitude):
    global adapter
    global device

    bArr = bytearray(95)
    # fixed data
    bArr[0:1] = bytearray.fromhex("00 5D")
    bArr[2:10] = bytearray.fromhex("08 02 FC 03 00 00 10 10 10")

    # position information
    bArr[11:18] = set_location(latitude,longitude)

    # get the timezone based on the position
    obj = TimezoneFinder()
    timezone = obj.timezone_at(lng=longitude, lat=latitude)


    # time information based on position data using timezone
    tz = pytz.timezone(timezone)
    bArr[19:25] = set_date(tz)
    # OR time information gained by library
    # bArr[19:25] = set_date()


    # Set the last offsets
    # timezone offset
    dt = datetime.utcnow()
    offset_min = int(tz.utcoffset(dt).seconds/ 60)
    offset_minBytes = offset_min.to_bytes(2, byteorder='big')

    # dst offset
    offset_dst_min = int(tz.dst(dt).seconds/60)
    offset_dst_minBytes = offset_dst_min.to_bytes(2, byteorder='big')

    bArr[91:92] = offset_minBytes
    bArr[93:94] = offset_dst_minBytes

    # write the location 
    # uuid = 0000dd11-0000-1000-8000-00805f9b34fb
    # handle = 61
    # print(bArr)
    print(binascii.hexlify(bArr))
    try:
        device.char_write_handle(61,bArr,wait_for_response=True)
    except pygatt.exceptions.NotConnectedError:
        print("Failed to connect to write message")


def sony_init():
    """
        Main function. The comments below try to explain what each section of
        the code does.
    """

    # pygatt uses pexpect and if your device has a long list of characteristics,
    # pexpect will not catch them all. We increase the search window to
    # 2048 bytes for the this example. By default, it is 200.
    # Note: We need an instance of GATToolBackend per each device connection

    global adapter
    global device
    adapter = pygatt.GATTToolBackend(search_window_size=2048)

    try:
        # Start the adapter
        adapter.start(False,4)
        # Connect to the device with that given parameter.
        # For scanning, use adapter.scan()
        print("Connecting...")
        try:
            device = adapter.connect(DEVICE)
            # print("Connected")
        except pygatt.exceptions.NotConnectedError:
            return False        
        
        # Set the security level to medium
        device.bond()
        # time.sleep(10)

        #set value for the mtu based on android apk
        device.exchange_mtu(158)

        # print("Present the characteristics")

        # # do the subscription in topics
        # device.subscribe("0000cc01-0000-1000-8000-00805f9b34fb",callback=handle_data)
        # device.subscribe("0000dd01-0000-1000-8000-00805f9b34fb",callback=handle_data,wait_for_response=False)
        # device.subscribe("0000cc05-0000-1000-8000-00805f9b34fb",callback=handle_data,wait_for_response=False)
        # device.subscribe("0000ff02-0000-1000-8000-00805f9b34fb",callback=handle_data,wait_for_response=False)

        # for uuid in device.discover_characteristics().keys():
        #     try:
        #         print("Read UUID %s: %s" % (uuid, binascii.hexlify(device.char_read(uuid))))
        #     except:
        #         continue
        
        return myConnectionTest()
    except:
        print("Couldn't connect at this try")
        return False

       

def isBlueConnected():
    global adapter
    global device
    mybArr = bytearray(1)
    if(myConnectionTest() and device._connected ): return True
    else:
        for i in range(blueTryConnectTimes):
            print("Try to connect ", i+1 , " of " ,blueTryConnectTimes)
            if(sony_init()): 
                return True

        print("Cannot connect to camera, exit")
        return False

def GetLocationInformation():
    return struct{}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose","-v", help="print debug", action="store_true")
    parser.add_argument("--lat", help="fixed lat", type=float)
    parser.add_argument("--lon", help="fixed lon", type=float)
    
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if(isBlueConnected() == False):
        print("We didn't managed to connect")

    if args.lat and args.lon:
        print("using provided fixed static gps")
    else:
        # Set fake pos data
        # Toumba Stadium Thessaloniki, Greece
        # 40.614380674810334, 22.971624208899676
        args.lat = 40.614380674810334
        args.lon = 22.971624208899676


    while True:
            
            # Example for getting location from your source
            msg = GetLocationInformation()
            if(isBlueConnected()):
                if msg is not None:
                    if msg.get_type() != "BAD_DATA":
                        print("Sent mav msg ", msg.lat, " ",msg.lon)
                        sendToCamera(msg.lat,msg.lon)
                    else:                    
                        print("Bad Data, Send Fixed data ", args.lat, " " ,args.lon)
                        sendToCamera(args.lat,args.lon)   
                else:
                    print("Empty msg, Send Fixed data ", args.lat, " " ,args.lon)
                    sendToCamera(args.lat,args.lon)

                    if verbose:
                        print("timeout")
                    time.sleep(0.1)
            else:
                quit()

    
