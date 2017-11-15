# *-* coding: utf-8 *-*

# Ceph data placement test script
# Author:   Zheng Lu
# Contact:  zlu12@utk.edu
# Date:     1/21/2014

import os
import sys
import subprocess
from datetime import datetime
from time import time

os.system('clear')
print '-------'
print 'OSD Tester: add objects to the ceph system and output placement stats'
print '-------'
print 'Usage: python dptest.py [osd_num = 1024]'

def osd_calc_stat(p_res):
    '''Calculate average, variance, max and min of input dictionary'''
    total = 0
    max_num = 0
    for osd in p_res:
        total += p_res[osd]
        if p_res[osd] > max_num:
            max_num = p_res[osd]
    avg = float(total) / float(len(p_res))

    squared_diff = 0
    min_num = max_num
    for osd in p_res:
        squared_diff += (p_res[osd] - avg) ** 2
        if p_res[osd] < min_num:
            min_num = p_res[osd]
    var = float(squared_diff) / float(len(p_res))
    var = var ** 0.5

    return avg, var, max_num, min_num

print ''
print 'INFO: Prepare for the test!'
obj_num = 1024
err_cnt = 0
total_replica = 0
total_time = 0
placement_results = {}
test_file_content = 'Hello Ceph'

if len(sys.argv) > 1:
    obj_num = int(sys.argv[1])

# make a folder to store files and results
res_folder = 'test_{0}_osd_{1}'.format(obj_num, datetime.now().strftime('%H_%M_%S'))
if subprocess.call('mkdir {0}'.format(res_folder), shell = True) != 0:
    print 'ERROR: Can not create test result folder!'
    exit()
else:
    print 'INFO: Test files and results will be stored in {0}'.format(res_folder)

# create log file
log = open('{0}/log.txt'.format(res_folder), 'w')

# place objects
print ''
print 'Test Start!'
print 'INFO: Start pushing objects to Ceph, this may take awhile'
print '.......'
pi = 0
bi = 0
for i in range(obj_num):
    # show test progress
    pi += 1
    if pi == 50:
        bi += 1
        print '{0} data objects have been placed'.format(bi * 50)
        pi = 0

    # generate test files
    f = open('{0}/testfile{1}.txt'.format(res_folder, i), 'w')
    print>>f, '{0}{1}'.format(test_file_content, time())
    f.close()

    # push test object to ceph
    beg = time() # we use time to measure crush placement running time, not very accurate, but can meet our needs
    if subprocess.call('sudo rados put test-auto-obj-{0} {1}/testfile{0}.txt --pool=data'.format(i, res_folder), shell=True) != 0:
        print>>log, 'ERROR: Failed to push test object {0} to Ceph!'.format(i)
        err_cnt += 1
        continue

    # get the replica location
    p = subprocess.Popen(['sudo', 'ceph', 'osd', 'map', 'data', 'test-object-{0}'.format(i)], stdout = subprocess.PIPE)
    end = time()
    total_time += end - beg
    out, err = p.communicate()
    temp = out.split('[')
    temp = temp[2].split(']')
    temp = temp[0].split(',')
    locations = []
    for item in temp:
        locations.append(int(item))

    # analyze placement results
    if len(locations) == 0:
        print>>log, 'ERROR: Failed to place test object {0}'.format(i)
        err_cnt += 1
        continue

    total_replica += len(locations)
    for item in locations:
        if item in placement_results:
            placement_results[item] += 1
        else:
            placement_results[item] = 1

# generate statistic results and write to file
stat_file = open('{0}/stat.txt'.format(res_folder), 'w')
print>>stat_file, 'Statistics of Test {0}:'.format(res_folder)
print>>stat_file, '\n-------'
print>>stat_file, 'Overall'
print>>stat_file, '-------\n'
print>>stat_file, 'Total number of objects to be placed: {0}'.format(obj_num)
print>>stat_file, 'Number of objects that have been successfully placed: {0}'.format(obj_num - err_cnt)
avg_replica = float(total_replica) / float(obj_num - err_cnt)
avg_time = float(total_time) / float(obj_num - err_cnt)
print>>stat_file, 'Average number of replicas for each object: {0}'.format(avg_replica)
print>>stat_file, 'Average time for crush data placement: {0}'.format(avg_time)

print>>stat_file, '\n-------'
print>>stat_file, 'Replica distributions'
print>>stat_file, '-------\n'
print>>stat_file, 'Total number of used OSDs: {0}'.format(len(placement_results))
avg, var, max_num, min_num = osd_calc_stat(placement_results)
print>>stat_file, 'Average number of objects placed in OSDs: {0}'.format(avg)
print>>stat_file, 'Standard variance of objects placed in OSDs: {0}'.format(var)
print>>stat_file, 'Max number of objects placed in OSDs: {0}'.format(max_num)
print>>stat_file, 'Min number of objects placed in OSDs: {0}'.format(min_num)

print>>stat_file, '\n-------'
print>>stat_file, 'Replica details'
print>>stat_file, '-------\n'
print>>stat_file, 'NOTE: Number in () is difference from average'
for item in placement_results:
    print>>stat_file, 'Number of replicas in osd.{0}: {1}({2})'.format(item, placement_results[item], placement_results[item] - avg)
stat_file.close()

# finalize test, print results, removing test objects, etc
print ''
print 'Important test statistics:'
print 'STAT: Total number of objects to be placed: {0}'.format(obj_num)
print 'STAT: Number of objects that have been successfully placed: {0}'.format(obj_num - err_cnt)
print 'STAT: Average number of objects placed in OSDs: {0}'.format(avg)
print 'STAT: Standard variance of objects placed in OSDs: {0}'.format(var)
print 'STAT: Average time for crush data placement: {0}'.format(avg_time)
print 'INFO: Detailed statistics of test has been stored in {0}/stat.txt'.format(res_folder)
print 'INFO: Errors of test has been stored in {0}/log.txt'.format(res_folder)
print ''
print 'INFO: Test finished, clean temporary files and objects.'
print 'INFO: This may take awhile. Please do not interrupt'
for i in range(obj_num):
    subprocess.call('rm {1}/testfile{0}.txt'.format(i, res_folder), shell=True)
    subprocess.call('rados rm test-auto-obj-{0} --pool=data'.format(i), shell=True)

log.close()
print 'FINISH!'
