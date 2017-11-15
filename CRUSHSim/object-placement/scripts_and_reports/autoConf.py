# *-* coding: utf-8 *-*

# Ceph deployment auto configure
# Author:   Zheng Lu
# Contact:  zlu12@utk.edu
# Date:     1/21/2014

import sys
import time
import subprocess

print '-------'
print 'Ceph Auto Configuration Tool'
print '-------'
print 'Usage: python autoConf.py'

conf_file = 'ec2conf.txt'
osdPdev = 4
conf = open('{0}'.format(conf_file), 'r')

subprocess.call('echo "ubuntu ALL = (root) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/ubuntu', shell = True)
subprocess.call('sudo chmod 0440 /etc/sudoers.d/ubuntu', shell = True)

subprocess.call('ssh-keygen -t rsa -b 2048', shell = True)

all_private = ''
public = []
private = []
lines = conf.read().splitlines()
for l in lines:
    if 'ec2-' in l:
        public.append(l)
    if 'ip-' in l:
        private.append(l)
if len(public) != len(private):
    print 'ERROR: Number of private DNS not equals public DNS'

print public
print private

for i in public:
    subprocess.call('cat .ssh/id_rsa.pub | ssh -i ceph-zheng.pem ubuntu@{0} "cat - >> ~/.ssh/authorized_keys2"'.format(i), shell = True)

subprocess.call('wget -q -O- \'https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc\' | sudo apt-key add -', shell = True)
subprocess.call('echo deb http://ceph.com/debian-dumpling/ $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/ceph.list', shell = True)
subprocess.call('sudo apt-get update', shell = True)
subprocess.call('sudo apt-get install ceph-deploy', shell = True)

subprocess.call('ceph-deploy new {0}'.format(private[1]), shell = True)

for i in private:
    subprocess.call('ceph-deploy install {0}'.format(i), shell = True)
    all_private += '{0} '.format(i)

subprocess.call('ceph-deploy mon create {0}'.format(private[1]), shell = True)
subprocess.call('ceph-deploy gatherkeys {0}'.format(private[1]), shell = True)

for i in private:
    for j in range(osdPdev):
        subprocess.call('ceph-deploy osd prepare {0}:/home/ubuntu/osd{1}'.format(i, j), shell = True)
        subprocess.call('ceph-deploy osd activate {0}:/home/ubuntu/osd{1}'.format(i, j), shell = True)

subprocess.call('ceph-deploy admin {0}'.format(all_private), shell = True)
subprocess.call('sudo ceph osd pool set data pg_num 512'.format(all_private), shell = True)
print 'Wait for background job to finish...'
print 'This may take a while'
time.sleep(60)
subprocess.call('sudo ceph osd pool set data pgp_num 512'.format(all_private), shell = True)
