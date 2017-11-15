'''
Created on Jan 26, 2014

@author: zlu12@utk.edu
'''

import sys

class Osd():
    '''
    Class for osds
    '''
    Type_NonSSD = 1
    Type_SSD = 2
    def __init__(self, osd_no, osd_type):
        self.no = osd_no
        self.type = osd_type
        self.obj_list = {} # include object's id and [ranking, primary]
        # below is exclusive for SSD OSDs:
        self.threshold = 0
        self.no_obj_moved_to_ssd = 0

    def exist_objects(self, obj_id):
        if obj_id in self.obj_list:
            return True
        return False

    def add_objects(self, obj_id, obj_ranking, primary):
        if obj_id not in self.obj_list:
            self.obj_list[obj_id] = [obj_ranking, primary]
            if self.type == Osd.Type_SSD and obj_ranking > 0: # rank = 0 means assigned by regular rule
                self.no_obj_moved_to_ssd += 1
            return True
        else:
            # already there
            # print 'ERROR: Objects add error, {0} already in OSD{1}'.format(obj_id, self.no)
            return False

    def remove_objects(self, obj_id): # only use for update
        if obj_id in self.obj_list:
            del self.obj_list[obj_id]
            if self.type == Osd.Type_SSD:
                self.no_obj_moved_to_ssd -= 1
            return True
        else:
            # cannot find it
            print 'ERROR: Objects remove error, cannot find {0} in OSD{1}'.format(obj_id, self.no)
            return False

    def access_objects(self, obj_id):
        # add this access to the object's counter
        if obj_id in self.obj_list:
            self.obj_list[obj_id][0] += 1
            return True
        else:
            return False

    def update(self, crush_map, osd_list, new_weights, num_replicas, num_in_ssd):
        no_obj_moved = 0
        if self.type == Osd.Type_NonSSD:
            # get ssd threshold from crush map
            threshold = crush_map.threshold
            # compare local list with threshold
            for obj_id in self.obj_list.keys(): # only update when it's primary
                if self.obj_list[obj_id][1] == 0: 
                    continue
                if self.obj_list[obj_id][0] > threshold:
                    obj_ranking = self.obj_list[obj_id][0]
                    # remove the original data
                    flag = True
                    [res_len, res] = crush_map.get_mapping_using_rule(crush_map.RegRule, obj_id, new_weights, len(new_weights), num_replicas)
                    for osd_id in res:
                        if osd_list[osd_id].exist_objects(obj_id) == False:
                            flag = False
                            break;
                    if flag == True:
                        ssd_cnt = 0
                        for osd_id in res: # already have sufficient replica in ssd
                            if osd_list[osd_id].type == Osd.Type_SSD:
                                ssd_cnt += 1
                        if ssd_cnt >= num_in_ssd:
                            continue
                        for osd_id in res:
                            osd_list[osd_id].remove_objects(obj_id)
                    else:
                        flag = True
                        [res_len, res] = crush_map.get_mapping_using_rule(crush_map.NonSSDRule, obj_id, new_weights, len(new_weights), num_replicas)
                        for osd_id in res:
                            if osd_list[osd_id].exist_objects(obj_id) == False:
                                flag = False
                                break;
                        if flag == True:
                            for osd_id in res:
                                osd_list[osd_id].remove_objects(obj_id)
                    if flag == False:
                        print "ERROR: No Rule Applied when remove object {0} from regular osd".format(obj_id)

                    # move highly ranked data to ssd
                    if flag == True:
                        [res_len, res] = crush_map.get_mapping_using_rule(crush_map.SSDRule, obj_id, new_weights, len(new_weights), num_in_ssd)
                        osd_list[res[0]].add_objects(obj_id, obj_ranking, 1) # primary replica
                        for osd_id in res:
                            osd_list[osd_id].add_objects(obj_id, obj_ranking, 0) # slave replica
                            osd_ranking = 0
                        if num_replicas - num_in_ssd > 0:
                            [res_len, res] = crush_map.get_mapping_using_rule(crush_map.NonSSDRule, obj_id, new_weights, len(new_weights), num_replicas - num_in_ssd)
                            for osd_id in res:
                                osd_list[osd_id].add_objects(obj_id, obj_ranking, 0) # slave replica

        elif self.type == Osd.Type_SSD:
            no_obj_moved = self.no_obj_moved_to_ssd
            # find n objects with lowest ranking, move them from ssd to reg
            for i in range(self.no_obj_moved_to_ssd):
                # calc the obj with minimal ranking
                min_ranking = sys.maxsize
                min_id = 0
                for obj_id in self.obj_list:
                    if self.obj_list[obj_id][0] <= min_ranking:
                        min_ranking = self.obj_list[obj_id][0]
                        min_id = obj_id
                # remove the original data
                obj_id = min_id
                flag = True
                [res_len, res] = crush_map.get_mapping_using_rule(crush_map.SSDRule, obj_id, new_weights, len(new_weights), num_in_ssd)
                if num_replicas - num_in_ssd > 0:
                    [res_len, res2] = crush_map.get_mapping_using_rule(crush_map.NonSSDRule, obj_id, new_weights, len(new_weights), num_replicas - num_in_ssd)
                    res += res2
                for osd_id in res:
                    if osd_list[osd_id].exist_objects(obj_id) == False:
                        flag = False
                        break;
                if flag == True:
                    for osd_id in res:
                        osd_list[osd_id].remove_objects(obj_id)
                else:
                    flag = True
                    [res_len, res] = crush_map.get_mapping_using_rule(crush_map.RegRule, obj_id, new_weights, len(new_weights), num_replicas)
                    for osd_id in res:
                        if osd_list[osd_id].exist_objects(obj_id) == False:
                            flag = False
                            break;
                    if flag == True:
                        for osd_id in res:
                            osd_list[osd_id].remove_objects(obj_id)
                    if flag == False:
                        print "ERROR: No Rule Applied when remove object {0} from ssd osd".format(obj_id)

                # move lowest ranked data to regular osd
                if flag == True:
                    obj_ranking = min_ranking
                    [res_len, res] = crush_map.get_mapping_using_rule(crush_map.NonSSDRule, obj_id, new_weights, len(new_weights), num_replicas)
                    osd_list[res[0]].add_objects(obj_id, obj_ranking, 1) # primary replica
                    for osd_id in res:
                        osd_list[osd_id].add_objects(obj_id, obj_ranking, 0) # slave replica
                        min_ranking = 0

            # update threshold after moving objects
            self.threshold = sys.maxsize
            threshold_total = 0
            threshold_cnt = 0
            for obj_id in self.obj_list:
                threshold_total += self.obj_list[obj_id][0] 
                threshold_cnt += 1
            if threshold_cnt > 0:
                self.threshold = threshold_total / threshold_cnt + 1

            # update threshold in the crush map
            if self.threshold < sys.maxsize:
                crush_map.map_threshold(self.threshold)

        else:
            print 'ERROR: Invalid OSD type!'

        return [crush_map, osd_list, no_obj_moved]
