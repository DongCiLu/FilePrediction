import sys
import cPickle as pickle

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    # first parse the file into a file access matrix
    traceFN = 'datasets/longtermtrace.fo'
    N = int(raw_input('How many intervals do you want to use?'))
    L = int(raw_input('What is your lower filter?'))

    if len(sys.argv) > 1:
        traceFN = sys.argv[1]
    if traceFN == '1':
        # load from cached files
        print 'Load previous data from temporary file.'
        fileList, minT, maxT = pickle.load(open('temp.txt', 'rb'))
    else:
        curFiles = {}
        fileList = {}
        errCnt = 0
        totalCnt = 0
        with open(traceFN) as traceF:
            for line in traceF:
                totalCnt += 1
                #if 'RESTART' in line:
                #    print 'Reset Map'
                #    curFiles = {}
                #    continue
                segs = line.split(',')
                line = segs[0]
                ends = segs[len(segs)-1]
                segs = line.split('(')
                filekeys = segs[1]
                segs = segs[0].split(' ')
                if len(segs) < 9:
                    continue
                pid = segs[4]
                time = float(segs[7])
                if len(fileList) == 0:
                    minT = time
                maxT = time
                op = segs[8]
                fn = ''
                if op == 'open':
                    fn = filekeys.split('"')[1]
                    fd = ends.split('= ')[1]
                    fd = fd.strip('\n')
                    key = pid + '/' + fd
                    if is_number(fd) and key not in curFiles:
                        curFiles[key] = fn
                        if fn not in fileList:
                            fileList[fn] = []
                        fileList[fn].append(time)
                elif op == 'read' or op == 'write':
                    fd = filekeys
                    key = pid + '/' + fd
                    if key in curFiles:
                        fileList[curFiles[key]].append(time)
                    else:
                        errCnt += 1
                        #print 'key error{0}:{1}'.format(segs[0],key)
                elif op == 'close':
                    fd = filekeys
                    key = pid + '/' + fd
                    if key in curFiles:
                        del curFiles[key]

        print 'There are {0} of {1} errors'.format(errCnt, totalCnt)
        print 'Store results to temporary files.'
        pickle.dump((fileList, minT, maxT), open('temp.txt', 'wb'))
                
    step = float(maxT - minT) / N

    f = open('stat.txt', 'w')
    print 'Calculate the access frequency at each time slot...'
    for filename in fileList.keys():
        if len(fileList[filename]) < L:
            continue
        count = [0]*N
        for timestamp in fileList[filename]:
            count[int((timestamp - minT) / step)] += 1
        #f.writelines('{0}:{1}\n'.format(filename, count))
        f.writelines('{0}\n'.format(count))
    f.close()
    print 'Done!'
