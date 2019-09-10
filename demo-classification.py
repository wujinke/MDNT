#!python
# -*- coding: UTF8-*- #
'''
####################################################################
# Demo for classification.
# Yuchen Jin @ cainmagi@gmail.com
# Requirements: (Pay attention to version)
#   python 3.6
#   tensorflow r1.13+
#   numpy, matplotlib
# Test the performance of modern layers (advanced blocks) on
# classification task. By using different options, users could switch to
# different network structures.
# (1) Assign the network
#     using `-nw` to assign the network type, for example, training
#     a inception network requires:
#     ```
#     python demo-classification.py -m tr -nw ince -s tiinst -mm inst
#     ```
# (2) Use different normalization.
#     `-mm` is used to assign the normalization type, for example,
#     training a network with batch normalization:
#     ```
#     python demo-classification.py -m tr -s trbatch -mm batch
#     ```
# (3) Use different dropout.
#     `-md` is used to set dropout type. If setting a dropout, the
#     dropout rate would be 0.3. For example, use additive noise:
#     ```
#     python demo-classification.py -m tr -s trinst_d_add --mm inst --md add
#     ```
# (4) Reduce learning rate during training.
#     Tests prove that reducing learning rate would help training
#     loss converge better. However, the validation loss would be
#     worse in this case. Use `-rlr` to enable automatic learning
#     rate scheduler, `-slr` to enable manual learning rate
#     scheduler:
#     ```
#     python demo-classification.py -m tr -s trinst_lr -rlr --mm inst
#     ```
# (5) Use a different network block depth.
#     Use `-dp` to set depth. For different kinds of blocks, the
#     parameter `depth` has different meanings. For example, if
#     want to use a more narrow incept-plus, use:
#     ```
#     python demo-classification.py -m tr -nw incp -dp 1 -s tipinstd1 -mm inst
#     ```
# (6) Load a network and perform test.
#     Because the network configuration has also been saved, users
#     do not need to set options when loading a model, for example:
#     ```
#     python demo-classification.py -m ts -s trinst -rd model-...
#     ```
# Version: 1.26 # 2019/6/23
# Comments:
#    Update the API of manually switched optimizers to fix bugs and
#    get coherent to the newest MDNT.
# Version: 1.25 # 2019/6/21
# Comments:
# 1. Support two-phase optimizers.
# 2. Change the monitored measurement of ModelCheckpoint to
#    accuracy.
# Version: 1.23 # 2019/6/20
# Comments:
# 1. Enable the option for using a manual scheduling strategy.
# 2. Make the network configurations more similar to those of the
#    Keras example.
# 3. Enable the repetition option.
# Version: 1.21 # 2019/6/20
# Comments:
#   Enable the option for using a different optimizer.
# Version: 1.20 # 2019/6/19
# Comments:
#   Adjust the configuration of the network.
# Version: 1.10 # 2019/6/13
# Comments:
#   Enable training data augmentation.
# Version: 1.00 # 2019/6/13
# Comments:
#   Create this project.
####################################################################
'''

import tensorflow as tf
from tensorflow.keras.datasets import cifar10
import numpy as np
import random
import matplotlib.pyplot as plt

import mdnt
import os, sys
os.chdir(sys.path[0])
#mdnt.layers.conv.NEW_CONV_TRANSPOSE=False

classes_names = ['airplane', 'automobile', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck']

def plot_sample(x_test, x_input=None, labels=None, trueLabels=None, n=10):
    '''
    Plot the first n digits from the input data set
    '''
    plt.figure(figsize=(20, 4))
    rows = 1
    if x_input is not None:
        rows += 1
        
    def plot_row(x, row, n, i, labels=None):
        ax = plt.subplot(rows, n, i + 1 + row*n)
        plt.imshow(x[i].reshape(32, 32, 3))
        plt.gray()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        if labels is not None:
            ax.set_title(classes_names[labels[i]])
        
    for i in range(n):
        # display original
        row = 0
        plot_row(x_test, row, n, i, labels=trueLabels)
        if x_input is not None:
            # display reconstruction
            row += 1
            plot_row(x_input, row, n, i, labels=labels)
    plt.show()
    
def mean_loss_func(lossfunc, name=None, *args, **kwargs):
    def wrap_func(*args, **kwargs):
        return tf.keras.backend.mean(lossfunc(*args, **kwargs))
    if name is not None:
        wrap_func.__name__ = name
    return wrap_func

def get_network_handle(nwName):
    if nwName == 'res':
        return mdnt.layers.Residual2D, mdnt.layers.Residual2DTranspose
    elif nwName == 'resn':
        return mdnt.layers.Resnext2D, mdnt.layers.Resnext2DTranspose
    elif nwName == 'ince':
        return mdnt.layers.Inception2D, mdnt.layers.Inception2DTranspose
    elif nwName == 'incr':
        return mdnt.layers.Inceptres2D, mdnt.layers.Inceptres2DTranspose
    elif nwName == 'incp':
        return mdnt.layers.Inceptplus2D, mdnt.layers.Inceptplus2DTranspose

def get_normalization_handle(normName):
    if normName == 'batch':
        return tf.keras.layers.BatchNormalization
    elif normName == 'inst':
        return mdnt.layers.InstanceNormalization
    elif normName == 'group':
        return mdnt.layers.GroupNormalization
    else:
        return mdnt.layers.InstanceNormalization

def build_model(mode='bias', dropout=None, nwName='res', depth=None, blockLen=3):
    mode = mode.casefold()
    # Get network handles:
    Block, BlockTranspose = get_network_handle(nwName)
    Normalize = get_normalization_handle(mode)
    # Make configuration
    if not mode in ['batch', 'inst', 'group']:
        if mode == 'bias':
            mode = True
        else:
            mode = False
    cwkwargs = {
        'normalization': mode,
        'kernel_initializer': tf.keras.initializers.he_normal(),
        'kernel_regularizer': tf.keras.regularizers.l2(1e-4),
        'activation': 'relu'
    }
    kwargs = {
        'normalization': mode,
        'kernel_initializer': tf.keras.initializers.he_normal(),
        'kernel_regularizer': tf.keras.regularizers.l2(1e-4),
        'activation': 'relu'
    }
    if depth is not None:
        kwargs['depth'] = depth
    # Build the model
    channel_1 = 32  # 32 channels
    channel_2 = 64  # 64 channels
    channel_3 = 128 # 128 channels
    #channel_4 = 256 # 512 channels
    # this is our input placeholder
    input_img = tf.keras.layers.Input(shape=(32, 32, 3))
    # Create encode layers
    norm_input = Normalize(axis=-1)(input_img)
    conv_1 = mdnt.layers.AConv2D(channel_1, (3, 3), padding='same', **cwkwargs)(norm_input)
    for i in range(blockLen):
        conv_1 = Block(channel_1, (3, 3), **kwargs)(conv_1)
    conv_2 = Block(channel_2, (3, 3), strides=(2, 2), dropout=dropout, **kwargs)(conv_1)
    for i in range(blockLen):
        conv_2 = Block(channel_2, (3, 3), **kwargs)(conv_2)
    conv_3 = Block(channel_3, (3, 3), strides=(2, 2), dropout=dropout, **kwargs)(conv_2)
    for i in range(blockLen):
        conv_3 = Block(channel_3, (3, 3), **kwargs)(conv_3)
    conv_3 = Normalize(axis=-1)(conv_3)
    if kwargs['activation'] == 'prelu':
        conv_3 = tf.keras.layers.PReLU(shared_axes=[1,2])(conv_3)
    else:
        conv_3 = tf.keras.layers.Activation(kwargs['activation'])(conv_3)
    pool_1 = tf.keras.layers.AveragePooling2D((8,8))(conv_3)
    pool_1 = tf.keras.layers.Dropout(0.25)(pool_1)
    flat_1 = tf.keras.layers.Flatten()(pool_1)
    prediction = tf.keras.layers.Dense(10, activation='softmax', kernel_initializer=kwargs['kernel_initializer'])(flat_1)
    # this model maps an input to its reconstruction
    classifier = tf.keras.models.Model(input_img, prediction)
    classifier.summary(line_length=90, positions=[.55, .85, .95, 1.])
    
    return classifier

if __name__ == '__main__':
    import argparse
    
    def str2bool(v):
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Unsupported value encountered.')
    
    parser = argparse.ArgumentParser(
        description='Perform classification on cifar10 dataset.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Parse arguments.
    
    parser.add_argument(
        '-m', '--mode', default='', metavar='str',
        help='''\
        The mode of this demo.
            tr (train): training mode, would train and save a network.
            ts (test) : testing mode, would reload a network and give predictions.
        '''
    )
    
    parser.add_argument(
        '-mm', '--modelMode', default='bias', metavar='str',
        help='''\
        The mode of this demo. (only for training)
            bias:  use biases instead of using normalization.
            batch: use batch normalization.
            inst : use instance normalization.
            group: use group normalization.
        '''
    )

    parser.add_argument(
        '-md', '--dropoutMode', default=None, metavar='str',
        help='''\
        The mode of dropout type in this demo. (only for training)
            None:    do not use dropout.
            plain:   use tf.keras.layers.Dropout.
            add:     use scale-invariant addictive noise.
            mul:     use multiplicative noise.
            alpha:   use alpha dropout.
            spatial: use spatial dropout.
        '''
    )

    parser.add_argument(
        '-nw', '--network', default='res', metavar='str',
        help='''\
        The basic network block. (only for training)
             res: residual block.
            resn: ResNeXt block.
            ince: inception block.
            incr: inception-residual block.
            incp: inception-plus block.
        '''
    )

    parser.add_argument(
        '-o', '--optimizer', default='amsgrad', metavar='str',
        help='''\
        The optimizer for training the network. When setting normalization as 'bias', the optimizer would be overrided by SGD+Momentum.
        '''
    )

    parser.add_argument(
        '-dp', '--blockDepth', default=None, type=int, metavar='int',
        help='''\
        The depth of each network block. (only for training)
        '''
    )

    parser.add_argument(
        '-rp', '--blockRepeat', default=3, type=int, metavar='int',
        help='''\
        The repetition of blocks in each stage. (only for training)
        '''
    )
    
    parser.add_argument(
        '-r', '--rootPath', default='checkpoints-cla', metavar='str',
        help='''\
        The root path for saving the network.
        '''
    )
    
    parser.add_argument(
        '-s', '--savedPath', default='model', metavar='str',
        help='''\
        The folder of the submodel in a particular train/test.
        '''
    )
    
    parser.add_argument(
        '-rd', '--readModel', default='model', metavar='str',
        help='''\
        The name of the model. (only for testing)
        '''
    )
    
    parser.add_argument(
        '-lr', '--learningRate', default=0.001, type=float, metavar='float',
        help='''\
        The learning rate for training the model. (only for training)
        '''
    )
    
    parser.add_argument(
        '-e', '--epoch', default=120, type=int, metavar='int',
        help='''\
        The number of epochs for training. (only for training)
        '''
    )
    
    parser.add_argument(
        '-tbn', '--trainBatchNum', default=32, type=int, metavar='int',
        help='''\
        The number of samples per batch for training. (only for training)
        '''
    )
    
    parser.add_argument(
        '-tsn', '--testBatchNum', default=10, type=int, metavar='int',
        help='''\
        The number of samples for testing. (only for testing)
        '''
    )
    
    parser.add_argument(
        '-sd', '--seed', default=None, type=int, metavar='int',
        help='''\
        Seed of the random generaotr. If none, do not set random seed.
        '''
    )

    parser.add_argument(
        '-rlr', '--reduceLR', type=str2bool, nargs='?', const=True, default=False, metavar='bool',
        help='''\
        Use the automatic learning rate reducing scheduler (would reduce LR to 0.001 of the initial configuration if need, and override the settings for learning rate scheduling). (only for training)
        '''
    )

    parser.add_argument(
        '-slr', '--scheduleLR', type=str2bool, nargs='?', const=True, default=False, metavar='bool',
        help='''\
        Use the manual learning rate scheduler (would reduce LR to 0.0005 of the initial configuration if need, the scheduling would be divided into 5 phases during the whole optimization). (only for training)
        '''
    )

    parser.add_argument(
        '-gn', '--gpuNumber', default=-1, type=int, metavar='int',
        help='''\
        The number of used GPU. If set -1, all GPUs would be visible.
        '''
    )
    
    args = parser.parse_args()
    def setSeed(seed):
        np.random.seed(seed)
        random.seed(seed+12345)
        tf.set_random_seed(seed+1234)
    if args.seed is not None: # Set seed for reproductable results
        setSeed(args.seed)
    if args.gpuNumber != -1:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpuNumber)
    
    def load_data():
        (x_train, y_train), (x_test, y_test) = cifar10.load_data()
        x_train = x_train.astype('float32') / 255.
        x_test = x_test.astype('float32') / 255.
        x_train = x_train.reshape(len(x_train), 32, 32, 3)
        x_test = x_test.reshape(len(x_test), 32, 32, 3)
        #plot_sample(x_train, n=10)

        y_train = tf.keras.utils.to_categorical(y_train, 10)
        y_test = tf.keras.utils.to_categorical(y_test, 10)
        return x_train, x_test, y_train, y_test
    
    if args.mode.casefold() == 'tr' or args.mode.casefold() == 'train':
        def lr_schedule(epoch):
            """Learning Rate Schedule

            Learning rate is scheduled to be reduced after 80, 120, 160, 180 epochs.
            Called automatically every epoch as part of callbacks during training.

            # Arguments
                epoch (int): The number of epochs

            # Returns
                lr (float32): learning rate
            """
            lr = args.learningRate
            if epoch > int(0.9*args.epoch):
                lr *= 0.5e-3
            elif epoch > int(0.8*args.epoch):
                lr *= 1e-3
            elif epoch > int(0.6*args.epoch):
                lr *= 1e-2
            elif epoch > int(0.4*args.epoch):
                lr *= 1e-1
            print('Learning rate: ', lr)
            return lr
        x_train, x_test, y_train, y_test = load_data()
        classifier = build_model(mode=args.modelMode, dropout=args.dropoutMode, nwName=args.network, depth=args.blockDepth, blockLen=args.blockRepeat)
        if args.modelMode.casefold() == 'bias':
            classifier.compile(optimizer=mdnt.optimizers.optimizer('nmoment', l_rate=args.learningRate), 
                                loss=tf.keras.losses.categorical_crossentropy, metrics=[tf.keras.metrics.categorical_accuracy])
        else:
            if args.optimizer == 'swats':
                optm = mdnt.optimizers.SWATS(lr=args.learningRate, amsgrad=False)
            elif args.optimizer == 'adam2sgd' or args.optimizer == 'amsgrad2sgd':
                enable_amsgrad = args.optimizer == 'amsgrad2sgd'
                optm = mdnt.optimizers.Adam2SGD(lr=args.learningRate, amsgrad=enable_amsgrad)
            elif args.optimizer == 'nadam2nsgd' or args.optimizer == 'namsgrad2nsgd':
                enable_amsgrad = args.optimizer == 'namsgrad2nsgd'
                optm = mdnt.optimizers.Nadam2NSGD(lr=args.learningRate, amsgrad=enable_amsgrad)
            else:
                optm = mdnt.optimizers.optimizer(args.optimizer, l_rate=args.learningRate)
            classifier.compile(optimizer=optm, 
                                loss=tf.keras.losses.categorical_crossentropy, metrics=[tf.keras.metrics.categorical_accuracy])
        
        folder = os.path.abspath(os.path.join(args.rootPath, args.savedPath))
        if os.path.abspath(folder) == '.' or folder == '':
            args.rootPath = 'checkpoints-cla'
            args.savedPath = 'model'
            folder = os.path.abspath(os.path.join(args.rootPath, args.savedPath))
        if tf.gfile.Exists(folder):
            tf.gfile.DeleteRecursively(folder)
        checkpointer = mdnt.utilities.callbacks.ModelCheckpoint(filepath=os.path.join(folder, 'model'), monitor='val_categorical_accuracy',
                                                                record_format='{epoch:02d}e-val_acc_{val_categorical_accuracy:.2f}.h5',
                                                                keep_max=5, save_best_only=True, verbose=1, period=5)
        tf.gfile.MakeDirs(folder)
        logger = tf.keras.callbacks.TensorBoard(log_dir=os.path.join('./logs-cla/', args.savedPath), 
            histogram_freq=(args.epoch//5), write_graph=True, write_grads=False, write_images=False, update_freq=10)
        if args.reduceLR:
            reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_categorical_accuracy', mode='max', factor=0.5, patience=5, min_lr=args.learningRate*0.001, verbose=1)
            get_callbacks = [checkpointer, logger, reduce_lr]
        elif args.scheduleLR:
            schedule_lr = tf.keras.callbacks.LearningRateScheduler(lr_schedule)
            get_callbacks = [checkpointer, logger, schedule_lr]
        else:
            get_callbacks = [checkpointer, logger]
        if args.optimizer in ('adam2sgd', 'amsgrad2sgd', 'nadam2nsgd', 'namsgrad2nsgd'):
            optmSwitcher = mdnt.utilities.callbacks.OptimizerSwitcher(int(0.2*args.epoch), verbose=1)
            get_callbacks.append(optmSwitcher)

        datagen = tf.keras.preprocessing.image.ImageDataGenerator(
            featurewise_center=False,  # set input mean to 0 over the dataset
            samplewise_center=False,  # set each sample mean to 0
            featurewise_std_normalization=False,  # divide inputs by std of the dataset
            samplewise_std_normalization=False,  # divide each input by its std
            zca_whitening=False,  # apply ZCA whitening
            zca_epsilon=1e-06,  # epsilon for ZCA whitening
            rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
            # randomly shift images horizontally (fraction of total width)
            width_shift_range=0.1,
            # randomly shift images vertically (fraction of total height)
            height_shift_range=0.1,
            shear_range=0.,  # set range for random shear
            zoom_range=0.,  # set range for random zoom
            channel_shift_range=0.,  # set range for random channel shifts
            # set mode for filling points outside the input boundaries
            fill_mode='nearest',
            cval=0.,  # value used for fill_mode = "constant"
            horizontal_flip=True,  # randomly flip images
            vertical_flip=False,  # randomly flip images
            # set rescaling factor (applied before any other transformation)
            rescale=None,
            # set function that will be applied on each input
            preprocessing_function=None,
            # image data format, either "channels_first" or "channels_last"
            data_format=None,
            # fraction of images reserved for validation (strictly between 0 and 1)
            validation_split=0.0
        )
        datagen.fit(x_train)
        classifier.fit_generator(datagen.flow(x_train, y_train, batch_size=args.trainBatchNum),
                    epochs=args.epoch,
                    validation_data=(x_test, y_test),
                    callbacks=get_callbacks)
    
    elif args.mode.casefold() == 'ts' or args.mode.casefold() == 'test':
        classifier = mdnt.load_model(os.path.join(args.rootPath, args.savedPath, args.readModel)+'.h5',
                                     headpath=os.path.join(args.rootPath, args.savedPath, 'model')+'.json')
        classifier.summary(line_length=90, positions=[.55, .85, .95, 1.])
        #for l in classifier.layers:
        #    print(l.name, l.trainable_weights)
        _, x_test, _, y_test = load_data()
        y_pred = classifier.predict(x_test[:args.testBatchNum, :])
        y_test = np.argmax(y_test, axis=1)
        y_pred = np.argmax(y_pred, axis=1)
        plot_sample(x_test[:args.testBatchNum, :], x_test[:args.testBatchNum, :], y_pred, y_test, n=args.testBatchNum)
    else:
        print('Need to specify the mode manually. (use -m)')
        parser.print_help()