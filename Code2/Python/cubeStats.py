#!/usr/bin/env python3
###
###  
###
### Jesse Leigh Patsolic 
### 2017 <jpatsol1@jhu.edu>
### S.D.G 
#
import argparse
import math
from intern.remote.boss import BossRemote
from intern.resource.boss.resource import *
import configparser
#import grequests # for async requests, conflicts with requests somehow
import requests
import numpy as np
from numpy import genfromtxt
import h5py
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import shutil
import blosc
from IPython.core.debugger import set_trace
import sys
import os
import itertools
from functools import partial
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import cpu_count
import csv
import datetime
import morton


def getCube(di):
    data = di['rem'].get_cutout(di['ch_rsc'], di['res'], di['xrng'],
          di['yrng'] ,di['zrng'])
    return(data)

def main(COLL_NAME, EXP_NAME, COORD_FRAME, LOCATIONS, BF = 5,
         CHAN_NAMES=None, num_threads = 4, CONFIG_FILE= 'config.ini'):

    L = genfromtxt(LOCATIONS,  delimiter=',', skip_header = 0, dtype='int32').tolist()
    m = morton.Morton(dimensions=3, bits=64)
    Lzo = sorted([m.pack(L[i][0], L[i][1], L[i][2]) for i in range(len(L))])

    loc = [m.unpack(l) for l in Lzo]

    if CHAN_NAMES is None:
        CHAN_NAMES = ['DAPI_1', 'DAPI_2', 'DAPI_3', 'DAPI_4', 'DAPI_5a',
                'DAPI_5b', 'DAPI_6', 'DAPI_7', 'GABAARa1_7', 'GAD2_4',
                'Gephyrin_1', 'GFP_5b', 'GluR1_5a', 'GluR2_6',
                'GluR4_7', 'NR2A_2', 'NR2B_4', 'PSD25_2', 'PV25_1',
                'Synapsin1_3', 'Synaptopodin_6', 'vGAT_3', 'vGluT1_3',
                'vGluT2_2', 'YFP_1']

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    TOKEN = config['Default']['token']
    boss_url = ''.join( ( config['Default']['protocol'],'://',config['Default']['host'],'/v1/' ) )
    #print(boss_url)
    #'https://api.boss.neurodata.io/v1/'
    
    #intern
    rem = BossRemote(CONFIG_FILE)

    x_rng = [[x[0]-BF, x[0]+BF+1] for x in loc] 
    y_rng = [[y[1]-BF, y[1]+BF+1] for y in loc] 
    z_rng = [[z[2]-BF, z[2]+BF+1] for z in loc]

    ChanList = []
    for ch in CHAN_NAMES:
        di = [{
              'rem': rem,
              'ch_rsc':
                ChannelResource(ch,COLL_NAME,EXP_NAME,'image',datatype='uint16'),
              'ch'  : ch,
              'res' : 0,
              'loc' : loc[i],
              'xrng': x_rng[i],  
              'yrng': y_rng[i],  
              'zrng': z_rng[i],  
              'bf'  : BF 
             } for i in range(len(loc))]
   
        with ThreadPool(num_threads) as tp:
            out = tp.map(getCube, di)
        ChanList.append(np.asarray(out))

    outArray = np.asarray(ChanList)
    return(outArray, loc)

def driveMain():
    COLL_NAME      = 'weiler14' 
    EXP_NAME       = 'Ex2R18C1' 
    COORD_FRAME    = 'weiler14_Ex2R18C1'
    LOCATIONS_FILE = 'testloc.csv'
    BF             = 5
    OUTPUT         = 'qwerty'
    CONFIG_FILE    = 'config.ini'

    CHAN_NAMES = ['DAPI_1', 'DAPI_2', 'DAPI_3', 'DAPI_4', 'DAPI_5a', 'DAPI_5b',
                      'DAPI_6', 'DAPI_7', 'GABAARa1_7', 'GAD2_4', 'Gephyrin_1',
                      'GFP_5b', 'GluR1_5a', 'GluR2_6', 'GluR4_7', 'NR2A_2',
                      'NR2B_4', 'PSD25_2', 'PV25_1', 'Synapsin1_3',
                      'Synaptopodin_6', 'vGAT_3', 'vGluT1_3', 'vGluT2_2', 'YFP_1']

    tmp, locs = main(COLL_NAME, EXP_NAME, COORD_FRAME, LOCATIONS_FILE, BF = 5,
         CHAN_NAMES=CHAN_NAMES, num_threads = 4, CONFIG_FILE= 'config.ini')
    return(tmp)
    
    
def testH5():
    a = np.arange(300).reshape(15, 2, 10)
    f = h5py.File("hdf5TEST_15_2_10.h5", 'w')
    dset = f.create_dataset("test", data = a)
    print(dset.shape())
    print(dset.dims())
    f.close()
   
    
def mainOUT(TOKEN,OUTPUT, out, L):
    h5f0OUT = h5py.File(OUTPUT+".h5", 'w')
    h5f0OUT.create_dataset(TOKEN + "_cubes", data = out)
    h5f0OUT.create_dataset("Locations", data = np.transpose(L))
    h5f0OUT.close()
    return(None)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = 
        'Download synapse cubes using the BOSS')
    parser.add_argument('-C', help='Valid collection id',
            type = str, metavar='C', default='weiler14')
    parser.add_argument('-E', help='Valid experiment id',
            type = str, metavar='E', default='Ex2R18C1')
    parser.add_argument('-F', help='valid coordinate frame', 
            type = str, metavar='F', default='weiler14_Ex2R18C1')
    parser.add_argument('-B', help='integer buffer around center',
            type = str, metavar='B', default=5)
    parser.add_argument('-L', help='csv file of locations '
            'in xyz order', type = str, metavar='L', required=True)
    parser.add_argument('-O', help='output filename',
            type = str, metavar='O', required=True,
            default = 'output')
    parser.add_argument('--con', help='user config file for BOSS'
            'authentication', type = str, metavar='con', required=True)
    
    args = parser.parse_args()

    COLL_NAME      = args.C
    EXP_NAME       = args.E
    COORD_FRAME    = args.F
    LOCATIONS_FILE = args.L 
    BF             = args.B
    OUTPUT         = args.O
    CONFIG_FILE    = args.con

    CHAN_NAMES = ['DAPI_1', 'DAPI_2', 'DAPI_3', 'DAPI_4', 'DAPI_5a', 'DAPI_5b',
                      'DAPI_6', 'DAPI_7', 'GABAARa1_7', 'GAD2_4', 'Gephyrin_1',
                      'GFP_5b', 'GluR1_5a', 'GluR2_6', 'GluR4_7', 'NR2A_2',
                      'NR2B_4', 'PSD25_2', 'PV25_1', 'Synapsin1_3',
                      'Synaptopodin_6', 'vGAT_3', 'vGluT1_3', 'vGluT2_2', 'YFP_1']

    cubes, locs = main(COLL_NAME, EXP_NAME, COORD_FRAME, 
                       LOCATIONS_FILE, BF = BF, 
                       CHAN_NAMES=CHAN_NAMES, 
                       num_threads = 4, CONFIG_FILE= CONFIG_FILE)

    
    mainOUT(EXP_NAME, OUTPUT, cubes, locs)
    print('Done!')

