# *-* coding: utf-8 *-*

# Ceph Auto Deployment Tool: OSD Folder Creator
# Author:   Zheng Lu
# Contact:  zlu12@utk.edu
# Date:     1/21/2014

import sys
import socket
import subprocess

print '-------'
print 'OSD Folder Creator, create folder with the name: hostname + id'
print '-------'
print 'Usage: python osdfolder.py osd_num'

if len(sys.argv) == 1:
    exit()

hostname = socket.gethostname()
l = hostname.split('-')
hostname = l[1]

for i in range(int(sys.argv[1])):
    foldername = '{0}{1}'.format(hostname, i)
    subprocess.call('mkdir {0}'.format(foldername), shell=True)
