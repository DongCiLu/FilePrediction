# *-* coding: utf-8 *-*

# Ceph Auto Deployment Tool: OSD Creator
# Author:   Zheng Lu
# Contact:  zlu12@utk.edu
# Date:     1/21/2014

import sys
import subprocess

devices = 4
total = 0
success = 0

print '-------'
print 'OSD Creator, will prepare and activate osd, follow the naming rule of osdfolder'
print '-------'
print 'Usage: python osdcreate.py osd_num [dev_num = 4]'

if len(sys.argv) == 1:
    exit()

osds = int(sys.argv[1])
if len(sys.argv) > 2:
    devices = int(sys.argv[2])

for i in range(devices):
    for j in range(osds):
        if subprocess.call('ceph-deploy osd prepare ceph-osd{0}:/home/ceph/osd{0}{1}'.format(i, j), shell = True) == 0:
            if subprocess.call('ceph-deploy osd activate ceph-osd{0}:/home/ceph/osd{0}{1}'.format(i, j), shell = True) == 0:
                success += 1
        total += 1

print 'Total tries: {0}\nSuccessful tries: {1}'.format(total, success)
