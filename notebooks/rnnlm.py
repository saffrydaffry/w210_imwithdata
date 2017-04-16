import time

import tensorflow as tf
import numpy as np


def matmul3d(X, W):
    """Wrapper for tf.matmul to handle a 3D input tensor X.
    Will perform multiplication along the last dimension.
  
    Args:
      X: [m,n,k]
      W: [k,l]
  
    Returns:
      XW: [m,n,l]
    """
    Xr = tf.reshape(X, [-1, tf.shape(X)[2]])
    XWr = tf.matmul(Xr, W)
    newshape = [tf.shape(X)[0], tf.shape(X)[1], tf.shape(W)[1]]
    return tf.reshape(XWr, newshape)


def MakeFancyRNNCell(H, keep_prob, num_layers=1):
    """Make a fancy RNN cell.
    James:  3-5 lines
  
    Use tf.nn.rnn_cell functions to construct an LSTM cell.
    Initialize forget_bias=0.0 for better training.
  
    Args:
      H: hidden state size
      keep_prob: dropout keep prob (same for input and output)
      num_layers: number of cell layers
  
    Returns:
      (tf.nn.rnn_cell.RNNCell) multi-layer LSTM cell with dropout
    """
    #### YOUR CODE HERE ####
    # cell = None  # replace with something better
    # cell = tf.nn.rnn_cell.BasicLSTMCell(num_units, forget_bias=1.0, input_size=10000, state_is_tuple=True, activation="tanh")
    cell = tf.contrib.rnn.BasicLSTMCell(num_units=H, state_is_tuple=True)
    # cell.num_units = 1
    cell.forget_bias = 0.0
    # Add dropout wrapperfor input on the single cell
    cell = tf.contrib.rnn.BasicRNNCell.DropoutWrapper(cell, input_keep_prob=keep_prob)
    # Build into a multi-layer cell
    cell = tf.contrib.rnn.MultiRNNCell([cell] * num_layers, state_is_tuple=True)

    # Add dropout wrapperfor output on the multi cell
    cell = tf.contrib.rnn.BasicRNNCell.DropoutWrapper(cell, output_keep_prob=keep_prob)
    cell.state_is_tuple = True
    return cell

    #### END(YOUR CODE) ####


class RNNLM(object):
    def __init__(self, V, H, num_layers=1):
        """Init function.
    
        This function just stores hyperparameters. You'll do all the real graph
        construction in the Build*Graph() functions below.
    
        Args:
          V: vocabulary size
          H: hidden state dimension
          num_layers: number of RNN layers (see tf.nn.rnn_cell.MultiRNNCell)
        """
        # Model structure; these need to be fixed for a given model.
        self.V = V
        self.H = H
        self.num_layers = num_layers  # Drew-mod:  Was previously 1

        # Training hyperparameters; these can be changed with feed_dict,
        # and you may want to do so during training.
        with tf.name_scope("Training_Parameters"):
            # learning_rate_init_ = tf.constant(0.1, name="learning_rate_init_")
            # self.learning_rate_ = tf.placeholder(dtype = tf.float32, name="learning_rate")
            self.learning_rate_ = tf.constant(0.1, dtype=tf.float32, name="learning_rate_")
            # self.dropout_keep_prob_ = tf.constant(0.5, name="dropout_keep_prob")
            self.dropout_keep_prob_ = tf.placeholder(tf.float32, name="dropout_keep_prob")
            # For gradient clipping, if you use it.
            # Due to a bug in TensorFlow, this needs to be an ordinary python
            # constant.
            self.max_grad_norm_ = 5.0

    def BuildCoreGraph(self):
        """Construct the core RNNLM graph, needed for any use of the model.
        James:  15-20 lines
    
        This should include:
        - Placeholders for input tensors (input_w, initial_h, target_y)
        - Variables for model parameters
        - Tensors representing various intermediate states
        - A Tensor for the output logits (logits_)
        - A scalar loss function (loss_)
    
        Your loss function should return a *scalar* value that represents the
        _summed_ loss across all examples in the batch (i.e. use tf.reduce_sum, not
        tf.reduce_mean).
    
        You shouldn't include training or sampling functions here; you'll do this
        in BuildTrainGraph and BuildSampleGraph below.
        """
        # Input ids, with dynamic shape depending on input.
        # Should be shape [batch_size, max_time] and contain integer word indices.
        self.input_w_ = tf.placeholder(tf.int32, [None, None], name="w")

        # Initial hidden state. You'll need to overwrite this with cell.zero_state
        # once you construct your RNN cell.
        self.initial_h_ = None

        # Output logits, which can be used by loss functions or for prediction.
        # Overwrite this with an actual Tensor of shape [batch_size, max_time]
        self.logits_ = None

        # Should be the same shape as inputs_w_
        self.target_y_ = tf.placeholder(tf.int32, [None, None], name="y")
        # self.target_y_ = tf.placeholder(tf.float32, [None, None, 1], name="y", )

        # Replace this with an actual loss function
        self.loss_ = None

        # Get dynamic shape info from inputs
        with tf.name_scope("batch_size"):
            self.batch_size_ = tf.shape(self.input_w_)[0]
        with tf.name_scope("max_time"):
            self.max_time_ = tf.shape(self.input_w_)[1]

        # Get sequence length from input_w_.
        # This will be a vector with elements ns[i] = len(input_w_[i])
        # You can override this in feed_dict if you want to have different-length
        # sequences in the same batch, although you shouldn't need to for this
        # assignment.
        self.ns_ = tf.tile([self.max_time_], [self.batch_size_, ], name="ns")

        #### YOUR CODE HERE ####

        # Construct embedding layer
        with tf.variable_scope("embedding"):
            mInit = tf.random_uniform_initializer(minval=-1, maxval=1, dtype=tf.float32, seed=0)
            embeddings = tf.get_variable(initializer=mInit, shape=[self.V, self.H], dtype=tf.float32, name="embeddings")
            # Reshape input tensor
            # self.input_w_ = tf.reshape( self.input_w_, [ -1, self.max_time_] )
            # Do embedding lookup
            cellInputs = tf.nn.embedding_lookup(embeddings, self.input_w_, name="cellInputs")
            # cellInputs now has dimensions batch_size x maxTime x H

            # Construct RNN/LSTM cell and recurrent layer
        with tf.variable_scope("recurrent"):
            cell = MakeFancyRNNCell(self.H, keep_prob=self.dropout_keep_prob_, num_layers=self.num_layers)
            # Initialize cell state
            self.initial_h_ = cell.zero_state(batch_size=self.batch_size_, dtype=tf.float32)
            rnn_outputs, final_state = tf.nn.dynamic_rnn(cell, cellInputs, initial_state=self.initial_h_)

            # output layer dimension is [batch_size, max_time,H]
        with tf.variable_scope("softmax"):
            # Drew changes
            # Wout = tf.get_variable(name = 'Wout', shape = [self.H, self.V])
            Wout = tf.get_variable(name='Wout', shape=[self.H, 2])
            # bout = tf.get_variable(name = 'bout', shape = [self.V,], initializer = tf.constant_initializer(0.0))
            bout = tf.get_variable(name='bout', shape=[2, ], initializer=tf.constant_initializer(0.0))

            # Drew:  In order to get 2 classes (1 or 0) we need the labels to be dim [batch, maxtime, 2]
            # ...for this we need a one-hot function to convert our 1dim label to one-hot 2class tensor
            self.y_label_ = tf.one_hot(indices=self.target_y_, depth=2)

            # Stuff Wout and bout into rnn instance
            self.wout_ = Wout
            self.bout_ = bout
            self.rnn_outputs_ = rnn_outputs
            # Softmax output layer, over vocabulary
            # Hint: use the matmul3d() helper here.
            self.logits_ = tf.add(matmul3d(rnn_outputs, Wout), bout)
            # Loss computation (true loss, for prediction)
            # For prediction, better to use full softmax instead of sampled softmax (used only for training...)
            # self.loss_ = tf.reduce_sum(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=self.logits_, labels=self.target_y_))
            # Drew:  We should use regular softmax, not sparse since it's only a binary classification
            # type of labels and logits must be the same and have same shape...

            # This is good.  Classes (1 | 0) are perfectly mutually exclusive since 1 = 1 - 0...
            # Must reshape logits and y to have rank = 2 with [batch x max_time, 2]...
            reshape_logits_ = tf.reshape(self.logits_, shape=[-1, 2])
            self.reshape_y_label_ = tf.reshape(self.y_label_, shape=[-1, 2])

            # Output softmax to get the actual prediction
            self.softmax_ = tf.nn.softmax(logits=reshape_logits_, name='softmax')
            self.loss_ = tf.reduce_sum(
                tf.nn.softmax_cross_entropy_with_logits(logits=reshape_logits_, labels=self.reshape_y_label_,
                                                        name="Loss"))

            # Drew:  The below op isn't working at least with how I'm initializing self.reshape_y_label_ ...
            # self.precision_ = tf.contrib.metrics.streaming_recall(predictions = self.softmax_, labels = self.reshape_y_label_)

            #### END(YOUR CODE) ####

    def BuildTrainGraph(self):
        """Construct the training ops.
        James: 6-12 lines
    
        You should define:
        - train_loss_ (optional): an approximate loss function for training
        - train_step_ : a training op that can be called once per batch
    
        Your loss function should return a *scalar* value that represents the
        _summed_ loss across all examples in the batch (i.e. use tf.reduce_sum, not
        tf.reduce_mean).
        """
        # Replace this with an actual training op
        self.train_step_ = tf.no_op(name="dummy")

        # Replace this with an actual loss function
        self.train_loss_ = None

        #### YOUR CODE HERE ####

        # Define loss function(s)
        with tf.name_scope("Train_Loss"):
            # Placeholder: replace with a sampled loss (sampled softmax...
            self.train_loss_ = self.loss_

        # Define optimizer and training op
        with tf.name_scope("Training"):
            optimizer_ = tf.train.AdagradOptimizer(self.learning_rate_)
            self.train_step_ = optimizer_.minimize(self.train_loss_)

            #### END(YOUR CODE) ####

    def BuildSamplerGraph(self):
        """Construct the sampling ops.
    
        You should define pred_samples_ to be a Tensor of integer indices for
        sampled predictions for each batch element, at each timestep.
    
        Hint: use tf.multinomial, along with a couple of calls to tf.reshape
        """
        # Replace with a Tensor of shape [batch_size, max_time, 1]
        self.pred_samples_ = None

        #### YOUR CODE HERE ####
        # with tf.name_scope("Sample_Prediction"):
        #  self.pred_samples_ = tf.reshape(tf.multinomial(tf.reshape(self.logits_,[-1,self.V]), 1, name = "pred_samples"), [ self.batch_size_, self.max_time_, 1 ])


        #### END(YOUR CODE) ####

