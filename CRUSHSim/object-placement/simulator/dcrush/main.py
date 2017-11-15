'''
Created on Jan 4, 2014

@author: lwan1@utk.edu, zlu12@utk.edu
'''
from crush_bucket import *
from crush_hash import *
from crush_rule import *
from crush_map import *
from crush_dyn import *
from copy import deepcopy
import random
import sys

def buckettype_to_number(buckettype):
    if buckettype == 'uniform':
        return 1
    elif buckettype == 'list':
        return 2
    elif buckettype == 'tree':
        return 3
    elif buckettype == 'straw':
        return 4
    else:
        return 0

def build_crush_map(num_osds, layers):
    '''
    build a CRUSH map with fixed number of osds and pre-configured storage hierarchy as input
    '''
    crush_map = CrushMap()
    osd_list = []
    SSD_cluster_layer = 4 # ssd cluster root will be a datacenter
    SSD_percentage = 0.1
    total_osds = num_osds

    non_ssd_root_id = 0
    ssd_root_id = 0
    for ig in range(2): # first loop for non ssd, second loop for ssd
        if ig == 0:
            num_osds = int(total_osds * (1 - SSD_percentage))
            lower_pos_offset = 0

        if ig == 1:
            stored_items = deepcopy(lower_items)
            stored_weights = deepcopy(lower_weights)
            lower_pos_offset = num_osds # start from ssd osds
            num_osds = total_osds

        type = 1
        lower_items = []
        lower_weights = []
        for i in range(num_osds):
            lower_items.append(i)
            lower_weights.append(0x10000)

        for row in layers: # create for regular osds
            if ig == 0 and type > SSD_cluster_layer:
                break
            layer_name = row[0]
            layer_buckettype = row[1]
            layer_size = row[2]
            buckettype_in_num = buckettype_to_number(layer_buckettype)
            if buckettype_in_num == 0:
                print 'unknown bucket type!'
            cur_items = []
            cur_weights = []
            lower_pos = lower_pos_offset
            while True:
                last_lower_pos = lower_pos
                if lower_pos == len(lower_items):
                    break
                items = [None]*num_osds
                weights = [0]*num_osds
                weight = 0
                for j in range(layer_size):
                    if layer_size == 0:
                        break
                    items[j] = lower_items[lower_pos]
                    weights[j] = lower_weights[lower_pos]
                    weight += weights[j]
                    lower_pos += 1
                    if lower_pos == len(lower_items):
                        break
                hash = CrushHash()
                if buckettype_in_num == 1:
                    bucket = UniformCrushBucket()
                    if j+1 and weights:
                        item_weight = weights[0]
                    else:
                        item_weight = 0
                    bucket.make_bucket(hash, type, j+1, items, item_weight)
                elif buckettype_in_num == 2:
                    bucket = ListCrushBucket()
                    bucket.make_bucket(hash, type, j+1, items, weights)
                elif buckettype_in_num == 3:
                    bucket = TreeCrushBucket()
                    bucket.make_bucket(hash, type, j+1, items, weights)
                elif buckettype_in_num == 4:
                    bucket = StrawCrushBucket()
                    bucket.make_bucket(hash, type, j+1, items, weights)
                bucket_id = crush_map.add_bucket(bucket, 0)
                if ig == 0:
                    non_ssd_root_id = bucket_id
                elif ig == 1:
                    root_id = bucket_id
                cur_items.append(bucket_id)
                cur_weights.append(weight)
                # create empty osd
                if type == 1:
                    if ig == 0:
                        for osd_no in range(last_lower_pos, lower_pos):
                            osd_list.append(Osd(osd_no, Osd.Type_NonSSD))
                    else:
                        for osd_no in range(last_lower_pos, lower_pos):
                            osd_list.append(Osd(osd_no, Osd.Type_SSD))
            lower_items = deepcopy(cur_items)
            lower_weights = deepcopy(cur_weights)
            if type == SSD_cluster_layer and ig == 1: # combine the two branch
                ssd_root_id = root_id
                stored_items += lower_items
                lower_items = stored_items
                stored_weights += lower_weights
                lower_weights = stored_weights
            lower_pos_offset = 0
            type += 1

    # regular rule set
    rule = CrushRule()
    rule.make_rule(3, 1, 1, 1, 10)
    rule.add_rule_step(CrushRuleStep(1, root_id, 0))
    rule.add_rule_step(CrushRuleStep(6, 0, 1))
    rule.add_rule_step(CrushRuleStep(4, 0, 0))
    crush_map.add_rule(rule, -1) # -1 means add new rule 

    # non ssd rule set
    rule = CrushRule()
    rule.make_rule(3, 2, 1, 1, 10) # len, rule_set no, type(replicated), min_size (not used), max_size (not used)
    rule.add_rule_step(CrushRuleStep(1, ssd_root_id, 0))
    rule.add_rule_step(CrushRuleStep(6, 0, 1))
    rule.add_rule_step(CrushRuleStep(4, 0, 0))
    crush_map.add_rule(rule, -1) # -1 means add new rule

    # ssd rule set
    rule = CrushRule()
    rule.make_rule(3, 3, 1, 1, 10) # len, rule_set no, type(replicated), min_size (not used), max_size (not used)
    rule.add_rule_step(CrushRuleStep(1, non_ssd_root_id, 0))
    rule.add_rule_step(CrushRuleStep(6, 0, 1))
    rule.add_rule_step(CrushRuleStep(4, 0, 0))
    crush_map.add_rule(rule, -1) # -1 means add new rule

    crush_map.finalize()
    return [crush_map, osd_list]

def print_crush_map(crush_map):
    for i in range(crush_map.max_buckets-1, -1, -1):
        if crush_map.crush_buckets[i] == None:
            continue
        print 'bucket id: '+str(crush_map.crush_buckets[i].id)
        print 'bucket weight: '+str(crush_map.crush_buckets[i].weight)
        print 'bucket type: '+crush_map.crush_buckets[i].get_alg_name(crush_map.crush_buckets[i].alg)
        print 'layer type: {0}'.format(crush_map.crush_buckets[i].type)
        items = [j for j in crush_map.crush_buckets[i].items if j != None]
        print 'items: '+str(items)
        print '********************************************************************************************************'

def print_replica_info(osd_list):
    for osd in osd_list:
        if osd.type == Osd.Type_NonSSD:
            print 'hdd',
        else:
            print 'ssd',
        for obj_id in osd.obj_list:
            #if osd.obj_list[obj_id] > 0:
                print '{0}'.format(osd.obj_list[obj_id]),
        print ',',
    print ' ' 
    
def adjust_weights(crush_map, weights, bucket_down_ratio, dev_down_ratio):
    '''
    adjust the device weight based on the bucket and device down ratio
    '''
    if dev_down_ratio > 0:
        w = weights
        bucket_ids = []
        for i in range(crush_map.max_buckets):
            b_id = -1-i
            if crush_map.crush_buckets[i]:
                bucket_ids.append(b_id)
        buckets_above_devices = []
        for i in range(len(bucket_ids)):
            b_id = bucket_ids[i]
            if crush_map.crush_buckets[-1-b_id].size == 0:
                continue
            first_child = crush_map.crush_buckets[-1-b_id].items[0]
            if first_child >= 0:
                buckets_above_devices.append(b_id)
        #permute bucket list
        for i in range(len(buckets_above_devices)):
            j = random.randint(0, pow(2, 31))%(len(buckets_above_devices)-1)
            buckets_above_devices[i], buckets_above_devices[j] = buckets_above_devices[j], buckets_above_devices[i]
        num_buckets_to_visit = int(bucket_down_ratio*len(buckets_above_devices))
        for i in range(num_buckets_to_visit):
            id = buckets_above_devices[i]
            size = crush_map.crush_buckets[-1-id].size
            items = []
            for j in range(size):
                items.append(crush_map.crush_buckets[-1-id].items[j])
            #permute item list
            for k in range(size):
                l = random.randint(0, pow(2, 31))%(size-1)
                items[k], items[l] = items[l], items[k]
            local_devices_to_visit = int(dev_down_ratio*size)
            for m in range(local_devices_to_visit):
                item = crush_map.crush_buckets[-1-id].items[m]
                w[item] = 0
        return w

def get_sys_throughput(crush_map, osd_list, new_weights, min_ruleno, max_ruleno, min_x, max_x, num_replicas, num_in_ssd):
    ssd_speed = 440
    hdd_speed = 110
    total_throughput = 0
    total_cnt = 0
    for obj_id in range(min_x, max_x+1):
        for r in range(min_ruleno, max_ruleno+1): 
            # run the crush rule in the order of: regular, ssd, non-ssd
            if r == crush_map.SSDRule:
                [res_len, res] = crush_map.get_mapping_using_rule(crush_map.SSDRule, obj_id, new_weights, len(new_weights), num_in_ssd) 
                if num_replicas - num_in_ssd > 0:
                    [res_len, res2] = crush_map.get_mapping_using_rule(crush_map.NonSSDRule, obj_id, new_weights, len(new_weights), num_replicas-num_in_ssd) 
                    res += res2
            else:
                [res_len, res] = crush_map.get_mapping_using_rule(r, obj_id, new_weights, len(new_weights), num_replicas) 
            obj_throughput = 0
            obj_freq = 0
            rep_cnt = 0
            for osd_id in res:
                if osd_list[osd_id].exist_objects(obj_id) != True:
                    break
                # read only
                if osd_list[osd_id].type == Osd.Type_SSD:
                    obj_throughput += ssd_speed
                else:
                    obj_throughput += hdd_speed
                # write only
                #if osd_list[osd_id].type == Osd.Type_SSD:
                #    obj_throughput = ssd_speed
                #else:
                #    obj_throughput = hdd_speed if obj_throughput < ssd_speed else ssd_speed
                rep_cnt += 1
            if rep_cnt == num_replicas:
                break
        if rep_cnt != num_replicas:
            print 'SYS_throughput: Cannot locate object{0}'.format(obj_id)
            continue
        obj_throughput = obj_throughput / num_replicas # only for read only
        obj_freq = osd_list[res[0]].obj_list[obj_id][0]
        total_throughput += obj_throughput * obj_freq
        total_cnt += obj_freq
    return [total_throughput, total_cnt]

def test_crush(crush_map, osd_list, min_x, max_x, num_replicas, dev_weights, bucket_down_ratio, dev_down_ratio, num_in_ssd, ruleno, show_details, niters):
    # change device weights
    weights = []
    for i in range(crush_map.max_devices):
        if i in dev_weights:
            weights.append(dev_weights[i])
        elif crush_map.item_exists(i):
            weights.append(0x10000)
        else:
            weights.append(0)
    new_weights = adjust_weights(crush_map, weights, bucket_down_ratio, dev_down_ratio)
    if new_weights == None:
        new_weights = weights

    total_iters = niters
    pre_sys_throughput = [0]*total_iters
    cur_sys_throughput = [0]*total_iters
    obj_moved = [0]*total_iters
    mul_factor = 1 # how many times(mul_factor*10) on average should an obj be accessed.
    standard_var_factor = 20
    niters = 0
    print 'iterate test {0} times with gauss distribution access pattern'.format(total_iters)
    print 'object ids from {0} to {1}'.format(min_x, max_x)
    print 'number of replicas: '+str(num_replicas)
    while niters < total_iters:
        print '---------------------------------'
        print 'start {0}th iteration'.format(niters+1)
        #print 'standard variance is set to {0}'.format((max_x - min_x + 1)/standard_var_factor)

        # clear the obj_list at each osd
        for osd in osd_list:
            osd.obj_list = {}
            osd.no_obj_moved_to_ssd = 0

        # add objects to osds using regular rule
        print 'start inserting objects with rule{0}'.format(ruleno)
        per = [0]*crush_map.max_devices
        for x in range(min_x, max_x+1):
            [res_len, res] = crush_map.get_mapping_using_rule(ruleno, x, new_weights, len(new_weights), num_replicas)
            if res_len < num_replicas:
                print x, res_len
            # add objects to osds
            if res_len > 0:
                osd_list[res[0]].add_objects(x, 0, 1) # primary replica
            for replica_no in res:
                osd_list[replica_no].add_objects(x, 0, 0)
                per[replica_no] +=1
        if show_details == 1:
            print 'times each device has been chosen when insert objects: '+str(per)

        # access data objects for required times
        min_ruleno = 0
        max_ruleno = 2
        event_len = max_x * mul_factor * 10
        found = False
        preset_threshold = 0
        for i in range(1, event_len+1):
            if i % (max_x*mul_factor) == 0:
                print "{0}0% access job has finished".format(i/(max_x*mul_factor))
            #x = random.randint(min_x, max_x) # uniform distribution
            x = int(random.gauss(float(min_x + max_x)/2, float(max_x - min_x + 1)/standard_var_factor)) # normal distribution
            if x == (min_x + max_x)/2:
                preset_threshold += 1
            if x < min_x or x > max_x:
                continue
            found = False
            for r in range(min_ruleno, max_ruleno+1): 
                # run the crush rule in the order of: regular, ssd, non-ssd
                num = num_replicas
                if r == crush_map.SSDRule:
                    num = num_in_ssd
                [res_len, res] = crush_map.get_mapping_using_rule(r, x, new_weights, len(new_weights), num) 
                found_cnt = 0
                for osd_id in res:
                    if osd_list[osd_id].exist_objects(x) == True: # if replica is still in that osd
                        found_cnt += 1
                    else:
                        break
                if found_cnt == res_len:
                    for osd_id in res:
                        osd_list[osd_id].access_objects(x)
                    found = True
                    break
            if found == False:
                print 'Access objects: Can not locate object{0}'.format(x)

        # reset crush_map threshold
        # crush_map.reset_threshold(int(preset_threshold * (2 ** 0.5) / 2))
        crush_map.clear_map_threshold()
        for osd in osd_list:
            if osd.type == Osd.Type_SSD:
                [crush_map, osd_list, no_obj_moved] = osd.update(crush_map, osd_list, new_weights, num_replicas, num_in_ssd)
        crush_map.threshold *= niters/(total_iters/3.0) + 1
        print 'Before data moving'
        print 'Threshold: {0}({1})'.format(crush_map.threshold, preset_threshold*(2**0.5)/2)
        if show_details == 1:
            print_replica_info(osd_list)

        # calc the throuput for each obj before apply data movement algorithm
        [pre_throughput, pre_cnt] = get_sys_throughput(crush_map, osd_list, new_weights, min_ruleno, max_ruleno, min_x, max_x, num_replicas, num_in_ssd)

        # run our algorithm
        crush_map.clear_map_threshold()
        for osd in osd_list:
            # note that only ssd osd will return non-zero no_obj_moved, multiply it by two will get the total no. of moved objects
            [crush_map, osd_list, no_obj_moved] = osd.update(crush_map, osd_list, new_weights, num_replicas, num_in_ssd)
            obj_moved[niters] += no_obj_moved
        obj_moved[niters] *= 2
        print 'After data moving'
        print 'Threshold: {0}'.format(crush_map.threshold)
        if show_details == 1:
            print_replica_info(osd_list)

        # calc the throuput for each obj after apply data movement algorithm
        [cur_throughput, cur_cnt] = get_sys_throughput(crush_map, osd_list, new_weights, min_ruleno, max_ruleno, min_x, max_x, num_replicas, num_in_ssd)

        pre_sys_throughput[niters] = pre_throughput / pre_cnt
        cur_sys_throughput[niters] = cur_throughput / cur_cnt
        #standard_var_factor -= 1
        niters += 1

    # print out results
    improve_ratio = []
    movement_ratio = []
    print '*********************************************'
    print 'result of all {0} tests\n'.format(total_iters)
    for  i, pre, cur, moved in zip(range(total_iters), pre_sys_throughput, cur_sys_throughput, obj_moved):
        print 'result for {0} iterations'.format(i+1)
        print 'system throughput before data movement: {0}'.format(pre)
        print 'system throughput after data movement: {0}'.format(cur)
        print 'no of moved objects: {0}%\n'.format(100*float(moved)/(max_x-min_x+1))
        movement_ratio.append(100*float(moved)/(max_x-min_x+1))
        improve_ratio.append(float(cur)/pre)
    print 'results vector'
    print 'data movement: {0}'.format(movement_ratio)
    print 'improvement ratio: {0}'.format(improve_ratio)
            
    return [crush_map, osd_list]

def main(niters, show_details):
    layers = []
    f1 = open('layers.txt', 'r')
    line_id = 0
    for line in f1:
        layer = []
        tmp = line.split()
        layer.append(tmp[0])
        layer.append(tmp[1])
        layer.append(int(tmp[2]))
        layers.append(layer)
        if show_details == 1:
            print 'layer '+str(line_id+1)+': '+str(layer)
        line_id += 1
    f1.close()
    print '*************************************************'
    args = {}
    f2 = open('args.txt', 'r')
    for line in f2:
        tmp = line.split()
        args[tmp[0]] = float(tmp[1]) if '.' in tmp[1] else int(tmp[1])
    f2.close()
    [crush_map, osd_list] = build_crush_map(args['num_osds'], layers)
    if show_details == 1:
        print_crush_map(crush_map)
        for osd in osd_list:
            print "osd{0}\ttype{1}".format(osd.no, osd.type)
    dev_weights = {}
    f3 = open('dev_weight.txt', 'r')
    for line in f3:
        tmp = line.split()
        w = int(float(tmp[1])*0x10000)
        if w < 0:
            w = 0
        if w > 0x10000:
            w = 0x10000
        dev_weights[int(tmp[0])] = w
    f3.close()
    [crush_map, osd_list] = test_crush(crush_map, osd_list, args['min_x'], args['max_x'], args['num_replicas'], dev_weights, args['bucket_down_ratio'], args['dev_down_ratio'], args['num_in_ssd'], 0, show_details, niters) #default ruleno always 0
    print 'done!'

if __name__ == '__main__':
    show_details = 0
    niters = 1
    if len(sys.argv) > 1:
        temp = int(sys.argv[1])
        if temp > 0:
            niters = temp
    if len(sys.argv) > 2:
        show_details = 1
    main(niters, show_details)
