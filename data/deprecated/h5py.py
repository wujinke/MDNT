'''
################################################################
# Data - h5py (deprecated)
# @ Modern Deep Network Toolkits for Tensorflow-Keras
# Yuchen Jin @ cainmagi@gmail.com
# Requirements: (Pay attention to version)
#   python 3.6+
#   tensorflow r1.13+
# Use tf-K standard dataset API to wrap the h5py APIs.
# Warning:
#   The standard tf dataset is proved to be incompatible with 
#   tf-K architecture. We need to wait until tf fix the bug.
# Version: 0.10 # 2019/3/26
# Comments:
#   Create this submodule.
################################################################
'''

import h5py
import numpy as np
import tensorflow as tf
import os

REMOVE_DEPRECATION = False

def depcatedInfo():
    try:
        raise DeprecationWarning('This library has been deprecated.')
    except Exception as e:
        if not REMOVE_DEPRECATION:
            raise e

class H5SupSaver:
    '''Save supervised data set as .h5 file
    This class allows users to dump multiple datasets into one file
    handle, then it would save it as a .h5 file. The keywords of the
    sets should be assigned by users.
    '''
    def __init__(self, fileName):
        '''
        Create the .h5 file while initialization.
        Arguments:
            fileName: a path where we save the file.
        '''
        self.f = None
        depcatedInfo()
        self.logver = 0
        self.__kwargs = dict()
        self.open(fileName)
        self.config(dtype='f')
        
    def config(self, **kwargs):
        '''
        Make configuration for the saver.
        Argumetns for this class:
            logver (int): the log level for dumping files.
        Arguments often used:
            chunks (tuple):         size of data blocks.
            compression (str):      compression method.
            compression_opts (int): compression parameter.
            shuffle (bool):         shuffle filter for data compression.
            fletcher32 (bool):      check sum for chunks.
        Learn more available arguments here:
            http://docs.h5py.org/en/latest/high/dataset.html
        '''
        logver = kwargs.pop('logver', None)
        if logver is not None:
            self.logver = logver
        self.__kwargs.update(kwargs)
        if self.logver > 0:
            print('Current configuration is:', self.__kwargs)
    
    def dump(self, keyword, data):
        '''
        Dump the dataset with a keyword into the file.
        Arguments:
            keyword: the keyword of the dumped dataset.
            data:    dataset, should be a numpy array.
        '''
        if self.f is None:
            raise OSError('Should not dump data before opening a file.')
        self.f.create_dataset(keyword, data=data, **self.__kwargs)
        if self.logver > 0:
            print('Dump {0} into the file. The data shape is {1}.'.format(keyword, data.shape))
    
    def open(self, fileName):
        '''
        The dumped file name (path), it will produce a .h5 file.
        Arguments:
            fileName: a path where we save the file.
        '''
        if fileName[-3:] != '.h5':
            fileName += '.h5'
        self.close()
        self.f = h5py.File(fileName, 'w')
        if self.logver > 0:
            print('Open a new file:', fileName)
        
    def close(self):
        if self.f is not None:
            self.f.close()
        self.f = None
        
class H5HGParser:
    '''Homogeneously parsing .h5 file by h5py module
    This class allows users to feed one .h5 file, and convert it to 
    tf.data.Dataset. The realization could be described as:
        (1) Create .h5 file handle.
        (2) Estimate the dataset size, and generate indexes.
        (3) Use the indexes to create a tf.data.Dataset, and allows it
            to randomly shuffle the indexes in each epoch.
        (4) Use Dataset.map() to address the data by the index from the
            index dataset.
    Note that in the file, there may be multiple datasets. This parser
    supports reading both single set and multiple sets.
    Note that all datasets in the same file should share the same shape.
    '''
    def __init__(self, fileName, batchSize=32):
        '''
        Create the parser and its h5py file handle.
        Arguments:
            fileName: the data path of the file (could be without postfix).
            batchSize: number of samples in each batch.
        '''
        self.f = None
        depcatedInfo()
        if (not os.path.isfile(fileName)) and (os.path.isfile(fileName+'.h5')):
            fileName += '.h5'
        self.f = h5py.File(fileName, 'r')
        self.size = self.__createSize()
        self.__dataset = self.__indexDataset()
        allNum = np.sum(self.size)
        self.__dataset = self.__dataset.shuffle(buffer_size=allNum)
        if self.mutlipleMode:
            self.__dataset = self.__dataset.map(lambda index: tf.py_function(self.__mapMultiple, [index], [tf.int32]))
        else:
            self.__dataset = self.__dataset.map(lambda index: tf.py_function(self.__mapSingle, [index], [tf.int32]))
        self.__dataset = self.__dataset.batch(batchSize)
        self.__dataset = self.__dataset.repeat()
        
    def getDataset(self):
        '''
        Get the produced tf dataset.
        '''
        return self.__dataset
        
    def __createSize(self):
        '''
        Find the number of items in the dataset, only need to be run for once.
        '''
        if len(self.f) == 1:
            self.mutlipleMode = False
            self.__dnameIndex = list(self.f.keys())[0]
            return len(self.f[self.__dnameIndex])
        else:
            self.mutlipleMode = True
            self.__dnameIndex = list(self.f.keys())
            return tuple(len(self.f[fk]) for fk in self.__dnameIndex)
        
    def __indexDataset(self):
        '''
        Create a tensorflow index dataset, only need to be run for once.
        Should be run after __createSize
        '''
        if self.mutlipleMode:
            def genOneIndex(num):
                return np.stack((num*np.ones(self.size[num], dtype=np.int), np.arange(self.size[num], dtype=np.int)), axis=1)
            indexes = np.concatenate(list(genOneIndex(n) for n in range(len(self.size))), axis=0)
            return tf.data.Dataset.from_tensor_slices(indexes)
        else:
            return tf.data.Dataset.from_tensor_slices(np.arange(self.size, dtype=np.int))
    
    def __mapMultiple(self, index):
        '''
        Map function, for multiple datasets mode.
        '''
        dname = self.__dnameIndex[index[0]]
        numSample = index[1]
        return self.f[dname][numSample]
        
    def __mapSingle(self, index):
        '''
        Map function, for multiple datasets mode.
        '''
        dname = self.__dnameIndex
        numSample = index
        return self.f[dname][numSample]
    
    def __del__(self):
        '''
        Destructor
        '''
        if self.f is not None:
            self.f.close()
            
class H5GParser:
    '''Grouply parsing dataset
    This class allows users to feed one .h5 file, and convert it to 
    tf.data.Dataset. The realization could be described as:
        (1) Create .h5 file handle.
        (2) Using the user defined keywords to get a group of datasets.
        (3) Estimate the dataset sizes, and generate indexes. Note each
            dataset should share the same size (but could be different 
            shapes).
        (4) Use the indexes to create a tf.data.Dataset, and allows it
            to randomly shuffle the indexes in each epoch.
        (5) Use Dataset.map() to address the data by the index from the
            index dataset.
    Certainly, you could use this parser to load a single dataset.
    '''
    def __init__(self, fileName, keywords, batchSize=32, preprocfunc=None):
        '''
        Create the parser and its h5py file handle.
        Arguments:
            fileName: the data path of the file (could be without postfix).
            keywords: should be a list of keywords (or a single keyword).
            batchSize: number of samples in each batch.
            preprocfunc: this function would be added to the produced data
                         so that it could serve as a pre-processing tool.
        '''
        self.f = None
        depcatedInfo()
        if isinstance(keywords, str):
            self.keywords = (keywords,)
        else:
            self.keywords = keywords
        if (not os.path.isfile(fileName)) and (os.path.isfile(fileName+'.h5')):
            fileName += '.h5'
        self.f = h5py.File(fileName, 'r')
        self.__dsets = self.__creatDataSets()
        self.size = self.__createSize()
        self.__dataset = self.__indexDataset()
        allNum = np.sum(self.size)
        self.__dataset = self.__dataset.shuffle(buffer_size=allNum)
        self.__dataset = self.__dataset.map(lambda index: tf.py_function(self.__mapSingle, [index], [tf.float32]*len(self.__dsets)))
        if preprocfunc is not None:
            self.__dataset = self.__dataset.map(preprocfunc)
        self.__dataset = self.__dataset.batch(batchSize)
        self.__dataset = self.__dataset.repeat()
        
    def getDataset(self):
        '''
        Get the produced tf dataset.
        '''
        return self.__dataset
        
    def __creatDataSets(self):
        '''
        Find all desired dataset handles, and store them.
        '''
        dsets = []
        for key in self.keywords:
            dsets.append(self.f[key])
        if not dsets:
            raise KeyError('Keywords are not mapped to datasets in the file.')
        return dsets
        
    def __createSize(self):
        '''
        Find the number of items in the dataset, only need to be run for once.
        Should be run after __creatDataSets.
        '''
        sze = len(self.__dsets[0])
        for dset in self.__dsets:
            if sze != len(dset):
                raise TypeError('The assigned keywords do not correspond to each other.')
        return sze
        
    def __indexDataset(self):
        '''
        Create a tensorflow index dataset, only need to be run for once.
        Should be run after __createSize.
        '''
        return tf.data.Dataset.from_tensor_slices(np.arange(self.size, dtype=np.int))

    def __mapSingle(self, index):
        '''
        Map function, for multiple datasets mode.
        '''
        return tuple(dset[index] for dset in self.__dsets)
    
    def __del__(self):
        '''
        Destructor
        '''
        if self.f is not None:
            self.f.close()