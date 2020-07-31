import pickle

A = {}
C = {}
S = {}
T = {}


def read_csv(fileName, dictName):
    with open(fileName, 'r') as f:
        for line in f.readlines():
            a = line.strip().split(',')
            assert len(a) == 2
            dictName[int(a[0])] = a[1]
    dictName[-1] = 'O'


read_csv('action.csv', A)
read_csv('capability.csv', C)
read_csv('strategicObjective.csv', S)
read_csv('tacticalObjective.csv', T)

with open('attrs.pkl', 'wb') as f:
    pickle.dump({'A': A, 'C': C, 'S': S, 'T': T}, f)
