lines = [line.strip() for line in open('result.csv')]
timestamps = []
fileids = []
for line in lines:
    substr = line.split(' ')
    timestamps.append(float(substr[0]))
    fileids.append(int(substr[1]))

N = int(raw_input('How many intervals do you want to use?'))
maxT = max(timestamps)
minT = min(timestamps)
maxF = max(fileids)
minF = min(fileids)
step = float(maxT - minT) / N

count = []
for i in range(maxF+1):
    count.append([0]*N)

for i in range(N):
    for timestamp, fid in zip(timestamps, fileids):
        if timestamp >= minT+i*step and timestamp <= minT+(i+1)*step:
            count[fid][i] += 1

f = open('stat.txt', 'w')
for i in range(maxF+1):
    f.writelines('{0}\n'.format(count[i]))
f.close()
