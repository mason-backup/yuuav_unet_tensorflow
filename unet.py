# coding:utf-8
"""module, define a unet network (supplying some-layer method and net method)

2018/11/19

Note:
    #  factor: Integer, upsampling factor
    # tf.stack() 矩阵拼接函数
    # logits output， -1 of reshape means that the axis is unknowing and will be  computed, (x, class_num).

    the first dimension of net input shape is the batch size, as the data feed into the neural network each time
    is a batch, not a single images, that why the input dimension is four (batch_size, h,w, d)

"""


import tensorflow as tf
from tensorflow.contrib.layers.python.layers import layers as tf_ctb_layers
from config import *
import numpy as np


def dense(input_, neural, name):
    dense = tf.layers.dense(input_, neural)
    logging.info("layer {0}, [{1}]".format(name, dense.shape))
    return dense


def conv_relu(input_, ksize, filter_num, name):
    _, h, w, d = input_.shape
    filter_shape = (ksize, ksize, input_.get_shape()[-1].value, filter_num)
    filter_ = tf.Variable(np.zeros(filter_shape, dtype=np.float32))
    bias = tf.Variable(np.zeros(filter_num, dtype=np.float32))

    conv = tf.nn.conv2d(input_, filter_, strides=[1, 1, 1, 1], padding="SAME")
    conv = tf.nn.bias_add(conv, bias)
    if batch_normalization:
        btn = tf_ctb_layers.batch_norm(conv, scale=True)
        output = tf.nn.relu(btn)
    else:
        output = tf.nn.relu(conv)
    logging.info("layer {0}, filter{1}, output{2}".format(name, filter_shape, output.shape))
    return output


def pool(input_, ksize, type_, name):
    if type_ == "max":
        pooling = tf.nn.max_pool(input_, [1, ksize, ksize, 1], strides=[1, ksize, ksize, 1], padding='SAME')
    else:
         pooling = tf.nn.avg_pool(input_, [1, ksize, ksize, 1], strides=[1, ksize, ksize, 1], padding='SAME')

    logging.info("layer {0}, [{1}]".format(name, pooling.shape))
    return pooling


def dropout(input_, keep_prob_, name):
    dropout_ = tf.nn.dropout(input_, keep_prob_)
    logging.info("layer {0}, [{1}]".format(name, dropout_.shape))
    return dropout_


def deconv(input_, filter_num, factor, name):
    _, h, w, d = input_.shape

    filter_shape = (h, w, d, filter_num)
    filter_ = tf.Variable(np.zeros(filter_shape, dtype=np.float32))

    bias_ = tf.Variable(np.zeros(filter_num, dtype=np.float32))

    output_shape_ = tf.stack([BS, h * factor, w * factor, d])

    deconv_ = tf.nn.conv2d_transpose(input_, filter_, output_shape=output_shape_,
                                     strides=[1, factor, factor, 1], padding="SAME")
    deconv_ = tf.nn.bias_add(deconv_, bias_)

    if batch_normalization:
        btn = tf_ctb_layers.batch_norm(deconv_, scale=True)
        output = tf.nn.relu(btn)
    else:
        output = tf.nn.relu(deconv_)
    logging.info("layer {0}, [{1}]".format(name, output.shape))
    return output


def unet(input_):
    inputs = input_
    logging.info("the input shape: {}".format(inputs.shape))
    net = {}

    # #############conv
    # block 1
    net['conv1_1'] = conv_relu(input_=inputs, ksize=3, filter_num=64, name="conv1_1")
    net['conv1_2'] = conv_relu(net['conv1_1'], 3, 64, "conv1_2")
    net['pool1'] = pool(net['conv1_2'], ksize=2, type_=max, name='pool1')

    # block 2
    net['conv2_1'] = conv_relu(net['pool1'], 3, 128, "conv2_1")
    net['conv2_2'] = conv_relu(net['conv2_1'], 3, 128, "conv2_2")
    net['pool2]'] = pool(net['conv2_2'], 2, max, 'pool2')

    # block 3
    net['conv3_1'] = conv_relu(net['pool2]'], 3, 256, "conv3_1")
    net['conv3_2'] = conv_relu(net['conv3_1'], 3, 256, "conv3_2")
    net['pool3'] = pool(net['conv3_2'], 2, max, 'pool3')
    net['dropout3'] = dropout(net['pool3'], keep_prob, name='dropout3')

    # block 4
    net['conv4_1'] = conv_relu(net['pool3'], 3, 512, "conv4_1")
    net['conv4_2'] = conv_relu(net['conv4_1'], 3, 512, "conv4_2")
    net['pool4'] = pool(net['conv4_2'], 2, max, 'pool4')
    net['dropout4'] = dropout(net['pool4'], keep_prob, name='dropout4')

    # block 5
    net['conv5_1'] = conv_relu(net['dropout4'], 3, 1024, "conv5_1")
    net['conv5_2'] = conv_relu(net['conv5_1'], 3, 1024, "conv5_2")
    net['dropout5'] = dropout(net['conv5_2'], keep_prob, name='dropout5')

    # #############deconv
    # block 6
    net['upsample6'] = deconv(net['dropout5'], 1024, 2, "upsample6")
    net['concat6'] = tf.concat([net['upsample6'], net['conv4_2']],axis=3,name='concat6')

    net['conv6_1'] = conv_relu(net['concat6'], 3, 512, "conv6_1")
    net['conv6_2'] = conv_relu(net['conv6_1'], 3, 512, "conv6_2")
    net['dropout6'] = dropout(net['conv6_2'], keep_prob, name='dropout6')

    # block 7
    net['upsample7'] = deconv(net['dropout6'], 512, 2, "upsample7")
    net['concat7'] = tf.concat([net['upsample7'], net['conv3_2']], axis=3, name='concat7')

    net['conv7_1'] = conv_relu(net['concat7'], 3, 256, "conv7_1")
    net['conv7_2'] = conv_relu(net['conv7_1'], 3, 256, "conv7_2")
    net['dropout7'] = dropout(net['conv7_2'], keep_prob, name='dropout7')

    # block 8
    net['upsample8'] = deconv(net['dropout7'], 256, 2, "upsample8")
    net['concat8'] = tf.concat([net['upsample8'], net['conv2_2']], axis=3, name='concat8')

    net['conv8_1'] = conv_relu(net['concat8'], 3, 128, "conv8_1")
    net['conv8_2'] = conv_relu(net['conv8_1'], 3, 128, "conv8_2")

    # block 9
    net['upsample9'] = deconv(net['conv8_2'], 128, 2, "upsample9")
    net['concat9'] = tf.concat([net['upsample9'], net['conv1_2']], axis=3, name='concat9')

    net['conv9_1'] = conv_relu(net['concat9'], 3, 64, "conv9_1")
    net['conv9_2'] = conv_relu(net['conv9_1'], 3, 64, "conv9_2")

    # block 10
    # the filter 3 is mean the image channel num
    net['conv10'] = tf.nn.conv2d(net['conv9_2'], filter=tf.Variable(np.zeros([1, 1, 64, 3], dtype=np.float32)),
                                 strides=[1, 1, 1, 1], padding="SAME", name='conv10')
    logging.info("the layer conv10 shape: {}".format(net["conv10"].shape))

    net['output'] = tf.reshape(net['conv10'], (-1, class_num))

    logging.info("the model output shape: {}".format(net["output"].shape))
    return net


