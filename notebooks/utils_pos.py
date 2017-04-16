import re
import time
import itertools
import numpy as np
import pandas as pd
import tensorflow as tf
from IPython.display import display


def flatten(list_of_lists):
    """Flatten a list-of-lists into a single list."""
    return list(itertools.chain.from_iterable(list_of_lists))


def pretty_print_matrix(M, rows=None, cols=None, dtype=float):
    """Pretty-print a matrix using Pandas.

    Args:
      M : 2D numpy array
      rows : list of row labels
      cols : list of column labels
      dtype : data type (float or int)
    """
    display(pd.DataFrame(M, index=rows, columns=cols, dtype=dtype))


def pretty_timedelta(fmt="%d:%02d:%02d", since=None, until=None):
    """Pretty-print a timedelta, using the given format string."""
    since = since or time.time()
    until = until or time.time()
    delta_s = until - since
    hours, remainder = divmod(delta_s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return fmt % (hours, minutes, seconds)


##
# Word processing functions
def canonicalize_digits(word):
    if any([c.isalpha() for c in word]): return word
    word = re.sub("\d", "DG", word)
    if word.startswith("DG"):
        word = word.replace(",", "")  # remove thousands separator
    return word


def canonicalize_word(word, wordset=None, digits=True):
    word = word.lower()
    if digits:
        if (wordset != None) and (word in wordset): return word
        word = canonicalize_digits(word)  # try to canonicalize numbers
    if (wordset == None) or (word in wordset):
        return word
    else:
        return "<unk>"  # unknown token


def canonicalize_words(words, **kw):
    return [canonicalize_word(word, **kw) for word in words]


##
# Data loading functions
import nltk
import vocabulary


def get_corpus(name="brown"):
    return nltk.corpus.__getattr__(name)


def build_vocab(corpus, V=10000):
    token_feed = (canonicalize_word(w) for w in corpus.words())
    vocab = vocabulary.Vocabulary(token_feed, size=V)
    return vocab


def get_train_test_sents(corpus, split=0.8, shuffle=True):
    """Get train and test sentences."""
    sentences = np.array(corpus.sents(), dtype=object)
    fmt = (len(sentences), sum(map(len, sentences)))
    print "Loaded %d sentences (%g tokens)" % fmt

    if shuffle:
        rng = np.random.RandomState(shuffle)
        rng.shuffle(sentences)  # in-place
    train_frac = 0.8
    split_idx = int(train_frac * len(sentences))
    train_sentences = sentences[:split_idx]
    test_sentences = sentences[split_idx:]

    fmt = (len(train_sentences), sum(map(len, train_sentences)))
    print "Training set: %d sentences (%d tokens)" % fmt
    fmt = (len(test_sentences), sum(map(len, test_sentences)))
    print "Test set: %d sentences (%d tokens)" % fmt

    return train_sentences, test_sentences


def preprocess_sentences(sentences, vocab):
    # Add sentence boundaries, canonicalize, and handle unknowns
    words = ["<s>"] + flatten(s + ["<s>"] for s in sentences)
    words = [canonicalize_word(w, wordset=vocab.word_to_id)
             for w in words]
    return np.array(vocab.words_to_ids(words))


##
# Use this function
def load_corpus(name, split=0.8, V=10000, shuffle=0):
    """Load a named corpus and split train/test along sentences."""
    corpus = get_corpus(name)
    vocab = build_vocab(corpus, V)
    train_sentences, test_sentences = get_train_test_sents(corpus, split, shuffle)
    train_ids = preprocess_sentences(train_sentences, vocab)
    test_ids = preprocess_sentences(test_sentences, vocab)
    return vocab, train_ids, test_ids


##
# Use this function
def batch_generator_pos(ids, posids, Ylabel, batch_size, max_time):
    """Convert ids to data-matrix form.
	This time, also generate pos_ids input """
    # Clip to multiple of max_time for convenience
    clip_len = ((len(ids) - 1) / batch_size) * batch_size
    input_w = ids[:clip_len]  # input words clipped to multiple of batch_size
    input_pos = posids[:clip_len]  # input word pos clipped to n*batch_size

    # Drew:  Modify to take input Ylabel
    target_y = Ylabel[:clip_len]  # clip Ylabel
    # Reshape so we can select columns
    input_w = input_w.reshape([batch_size, -1])
    input_pos = input_pos.reshape([batch_size, -1])
    target_y = target_y.reshape([batch_size, -1])
    # Yield batches
    for i in xrange(0, input_w.shape[1], max_time):
        yield input_w[:, i:i + max_time], input_pos[:, i:i + max_time], target_y[:, i:i + max_time]


def run_epoch_pos(lm, session, batch_iterator, train=False,
                  verbose=False, tick_s=10,
                  keep_prob=1.0, learning_rate=0.1):
    start_time = time.time()
    tick_time = start_time  # for showing status
    total_cost = 0.0  # total cost, summed over all words
    total_words = 0

    if train:
        train_op = lm.train_step_
        keep_prob = keep_prob
        loss = lm.train_loss_  # For our small dataset we're using softmax, not sampled_softmax for training.
    else:
        train_op = tf.no_op()
        keep_prob = 1.0  # no dropout at test time
        loss = lm.loss_  # true loss.

    for i, (w, pos, y) in enumerate(batch_iterator):
        cost = 0.0

        learning_rate = np.float32(learning_rate)
        keep_prob = np.float32(keep_prob)

        # At first batch in epoch, get a first initial state
        if i == 0:
            h, yHatRNN, hLabelRNN = session.run([lm.initial_h_, lm.softmax_,
                                                 lm.reshape_y_label_], feed_dict={lm.input_w_: w,
                                                                                  lm.input_pos_: pos,
                                                                                  lm.target_y_: y,
                                                                                  lm.learning_rate_: learning_rate,
                                                                                  lm.dropout_keep_prob_: keep_prob})

        # Run a training step and calculate the cost
        cost, h, _, used_learning_rate, used_keep_prob, y_2wide_Hats, y_2wide_Labels = session.run(
            [loss, lm.initial_h_, train_op, lm.learning_rate_, lm.dropout_keep_prob_, lm.softmax_, lm.reshape_y_label_],
            feed_dict={lm.input_w_: w, lm.input_pos_: pos, lm.target_y_: y, lm.initial_h_: h,
                       lm.learning_rate_: learning_rate, lm.dropout_keep_prob_: keep_prob})
        yHatRNN = np.concatenate((yHatRNN, y_2wide_Hats), axis=0)
        hLabelRNN = np.concatenate((hLabelRNN, y_2wide_Labels), axis=0)

        # Debugging
        # print "First row of w"
        # print w[0,:]
        # print(lm.input_w_)
        # print(lm.target_y_)

        #### END(YOUR CODE) ####
        total_cost += cost
        total_words += w.size  # w.size = batch_size * max_time

        ##
        # Drew, debug:
        # print "number of RNN layers:  %d" % (used_num_layers)
        # print "dropout keep probability setting:  %f" % (used_keep_prob)
        # print "learning rate:  %f" % (used_learning_rate)



        # Print average loss-so-far for epoch
        # If using train_loss_, this may be an underestimate.
        if verbose and (time.time() - tick_time >= tick_s):
            avg_cost = total_cost / total_words
            avg_wps = total_words / (time.time() - start_time)
            print "[batch %d]: seen %d words at %d wps, loss = %.3f" % (i,
                                                                        total_words, avg_wps, avg_cost)
            tick_time = time.time()  # reset time ticker

    return (total_cost / total_words), yHatRNN, hLabelRNN


def score_dataset_pos(lm, session, ids, pos, Ylabels, name="Data"):
    """
    score_dataset variables:
       ids:       input-word ids
       pos:		input-word part-of-speech ids
       Ylabels:   target labels, where good = 0 | bad = 1.
       yHat:      tf output prediction for good = 0 | bad = 1.
  
    It produces Correct = ( test_ids == testY )
  
    and calculates:
         Precision = Count( yHat == testY == 1 ) / Count( yHat == 1 )
         Recall = Count( yHat == testY == 1 ) / Count( testY == 1 )
    """
    bi = batch_generator_pos(ids, pos, Ylabels, batch_size=100, max_time=100)
    cost, y_2wide_Hats, y_2wide_Labels = run_epoch_pos(lm, session, bi,
                                                       learning_rate=1.0, keep_prob=1.0,
                                                       train=False, verbose=False, tick_s=3600)
    # print "%s: precision: %.03f  avg. loss: %.03f  (perplexity: %.02f)" % (name, precision, cost, np.exp(cost))
    print "%s: avg. loss: %.03f  (perplexity: %.02f)" % (name, cost, np.exp(cost))

    return y_2wide_Labels, y_2wide_Hats

