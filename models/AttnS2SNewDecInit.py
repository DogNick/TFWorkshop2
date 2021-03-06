#from __future__ import absolute_import
import time
import numpy as np
from ModelCore import *

import tensorflow as tf
from tensorflow.contrib import lookup
from tensorflow.python.ops import variable_scope
from tensorflow.python.framework import constant_op

from tensorflow.contrib.rnn import MultiRNNCell, AttentionCellWrapper, GRUCell, LSTMCell, LSTMStateTuple

from tensorflow.python.layers import core as layers_core
from tensorflow.contrib.seq2seq.python.ops import loss

import Nick_plan
from components import DecStateInit, AttnCell, DynRNN, CreateMultiRNNCell 
import logging as log

graphlg = log.getLogger("graph")

class AttnS2SNewDecInit(ModelCore):
	"""
		standard attention seq2seq
	"""
	def __init__(self, name, job_type="single", task_id=0, dtype=tf.float32):
		super(self.__class__, self).__init__(name, job_type, task_id, dtype) 
	
	def build_inputs(self, for_deploy):
		graphlg.info("Creating placeholders...")
		inputs = {
			"enc_inps:0":tf.placeholder(tf.string, shape=(None, self.conf.input_max_len), name="enc_inps"),
			"enc_lens:0":tf.placeholder(tf.int32, shape=[None], name="enc_lens")
		}
		# inputs for training period 
		#if not for_deploy or self.conf.variants == "score":
		inputs["dec_inps:0"] = tf.placeholder(tf.string, shape=[None, self.conf.output_max_len + 2], name="dec_inps")
		inputs["dec_lens:0"] = tf.placeholder(tf.int32, shape=[None], name="dec_lens")
		#if not self.conf.variants == "score":
		inputs["down_wgts:0"] = tf.placeholder(tf.float32, shape=[None], name="down_wgts")
		return inputs

	def build(self, inputs, for_deploy):
		conf = self.conf
		name = self.name
		job_type = self.job_type
		dtype = self.dtype
		self.beam_size = 1 if (not for_deploy or self.conf.variants=="score") else sum(self.conf.beam_splits)
		conf.keep_prob = conf.keep_prob if not for_deploy else 1.0

		self.enc_str_inps = inputs["enc_inps:0"]
		self.dec_str_inps = inputs["dec_inps:0"]
		self.enc_lens = inputs["enc_lens:0"] 
		self.dec_lens = inputs["dec_lens:0"]
		#self.down_wgts = inputs["down_wgts:0"]

		with tf.name_scope("TableLookup"):
			# lookup tables
			self.in_table = lookup.MutableHashTable(key_dtype=tf.string,
														value_dtype=tf.int64,
														default_value=UNK_ID,
														shared_name="in_table",
														name="in_table",
														checkpoint=True)

			self.out_table = lookup.MutableHashTable(key_dtype=tf.int64,
														 value_dtype=tf.string,
														 default_value="_UNK",
														 shared_name="out_table",
														 name="out_table",
														 checkpoint=True)
			self.enc_inps = self.in_table.lookup(self.enc_str_inps)
			self.dec_inps = self.in_table.lookup(self.dec_str_inps)

		# Create encode graph and get attn states
		graphlg.info("Creating embeddings and embedding enc_inps.")
		with ops.device("/cpu:0"):
			self.embedding = variable_scope.get_variable("embedding", [conf.output_vocab_size, conf.embedding_size])

		with tf.name_scope("Embed") as scope:
			dec_inps = tf.slice(self.dec_inps, [0, 0], [-1, conf.output_max_len + 1])
			with ops.device("/cpu:0"):
				self.emb_inps = embedding_lookup_unique(self.embedding, self.enc_inps)
				emb_dec_inps = embedding_lookup_unique(self.embedding, dec_inps)
		# output projector (w, b)
		with tf.variable_scope("OutProj"):
			if conf.out_layer_size:
				w = tf.get_variable("proj_w", [conf.out_layer_size, conf.output_vocab_size], dtype=dtype)
			elif conf.bidirectional:
				w = tf.get_variable("proj_w", [conf.num_units * 2, conf.output_vocab_size], dtype=dtype)
			else:
				w = tf.get_variable("proj_w", [conf.num_units, conf.output_vocab_size], dtype=dtype)
			b = tf.get_variable("proj_b", [conf.output_vocab_size], dtype=dtype)

		graphlg.info("Creating dynamic rnn...")
		self.enc_outs, self.enc_states, mem_size, enc_state_size = DynRNN(conf.cell_model, conf.num_units, conf.num_layers,
																			  self.emb_inps, self.enc_lens, keep_prob=conf.keep_prob,
																			  bidi=conf.bidirectional, name_scope="DynRNNEncoder")
		batch_size = tf.shape(self.enc_outs)[0]
		# to modify the output states of all encoder layers for dec init
		final_enc_states = self.enc_states


		with tf.name_scope("DynRNNDecode") as scope:
			with tf.name_scope("ShapeToBeam") as scope: 
				beam_memory = tf.reshape(tf.tile(self.enc_outs, [1, 1, self.beam_size]), [-1, conf.input_max_len, mem_size])
				beam_memory_lens = tf.squeeze(tf.reshape(tf.tile(tf.expand_dims(self.enc_lens, 1), [1, self.beam_size]), [-1, 1]), 1)
				def _to_beam(t):
					return tf.reshape(tf.tile(t, [1, self.beam_size]), [-1, int(t.get_shape()[1])])	
				beam_init_states = tf.contrib.framework.nest.map_structure(_to_beam, final_enc_states)

			max_mem_size = self.conf.input_max_len + self.conf.output_max_len + 2
			cell = AttnCell(cell_model=conf.cell_model, num_units=mem_size, num_layers=conf.num_layers,
							attn_type=self.conf.attention, memory=beam_memory, mem_lens=beam_memory_lens,
							max_mem_size=max_mem_size, addmem=self.conf.addmem, keep_prob=conf.keep_prob,
							dtype=tf.float32, name_scope="AttnCell")

			dec_init_state = DecStateInit(all_enc_states=beam_init_states, decoder_cell=cell, batch_size=batch_size * self.beam_size, init_type=conf.dec_init_type, use_proj=conf.use_init_proj)

			if not for_deploy: 
				hp_train = helper.ScheduledEmbeddingTrainingHelper(inputs=emb_dec_inps, sequence_length=self.dec_lens, 
																   embedding=self.embedding, sampling_probability=self.conf.sample_prob,
																   out_proj=(w, b))
				output_layer = layers_core.Dense(self.conf.out_layer_size, use_bias=True) if self.conf.out_layer_size else None
				my_decoder = basic_decoder.BasicDecoder(cell=cell, helper=hp_train, initial_state=dec_init_state, output_layer=output_layer)
				cell_outs, final_state = decoder.dynamic_decode(decoder=my_decoder, impute_finished=True, maximum_iterations=conf.output_max_len + 1, scope=scope)
			elif self.conf.variants == "score":
				hp_train = helper.ScheduledEmbeddingTrainingHelper(inputs=emb_dec_inps, sequence_length=self.dec_lens, embedding=self.embedding, sampling_probability=0.0,
																   out_proj=(w, b))
				output_layer = layers_core.Dense(self.conf.out_layer_size, use_bias=True) if self.conf.out_layer_size else None
				my_decoder = score_decoder.ScoreDecoder(cell=cell, helper=hp_train, out_proj=(w, b), initial_state=dec_init_state, output_layer=output_layer)
				cell_outs, final_state = decoder.dynamic_decode(decoder=my_decoder, scope=scope, maximum_iterations=self.conf.output_max_len, impute_finished=True)
			else:
				hp_infer = helper.GreedyEmbeddingHelper(embedding=self.embedding,
														start_tokens=tf.ones(shape=[batch_size * self.beam_size], dtype=tf.int32),
														end_token=EOS_ID, out_proj=(w, b))

				output_layer = layers_core.Dense(self.conf.out_layer_size, use_bias=True) if self.conf.out_layer_size else None
				dec_init_state = beam_decoder.BeamState(tf.zeros([batch_size * self.beam_size]), dec_init_state, tf.zeros([batch_size * self.beam_size], tf.int32))
				my_decoder = beam_decoder.BeamDecoder(cell=cell, helper=hp_infer, out_proj=(w, b), initial_state=dec_init_state,
														beam_splits=self.conf.beam_splits, max_res_num=self.conf.max_res_num, output_layer=output_layer)
				cell_outs, final_state = decoder.dynamic_decode(decoder=my_decoder, scope=scope, maximum_iterations=self.conf.output_max_len, impute_finished=True)

		if not for_deploy:	
			outputs = cell_outs.rnn_output
			# Output ouputprojected to logits
			L = tf.shape(outputs)[1]
			outputs = tf.reshape(outputs, [-1, int(w.shape[0])])
			outputs = tf.matmul(outputs, w) + b 
			logits = tf.reshape(outputs, [-1, L, int(w.shape[1])])

			# branch 1 for debugging, doesn't have to be called
			with tf.name_scope("DebugOutputs") as scope:
				self.outputs = tf.argmax(logits, axis=2)
				self.outputs = tf.reshape(self.outputs, [-1, L])
				self.outputs = self.out_table.lookup(tf.cast(self.outputs, tf.int64))

			with tf.name_scope("Loss") as scope:
				tars = tf.slice(self.dec_inps, [0, 1], [-1, L])

				# wgts may be a more complicated form, for example a partial down-weighting of a sequence
				# but here i just use  1.0 weights for all no-padding label
				wgts = tf.cumsum(tf.one_hot(self.dec_lens, L), axis=1, reverse=True)

				#wgts = wgts * tf.expand_dims(self.down_wgts, 1)

				loss_matrix = loss.sequence_loss(logits=logits, targets=tars, weights=wgts, average_across_timesteps=False, average_across_batch=False)

				self.loss = see_loss = tf.reduce_sum(loss_matrix) / tf.reduce_sum(wgts)

			with tf.name_scope(self.model_kind):
				tf.summary.scalar("loss", see_loss)

			graph_nodes = {
				"loss":self.loss,
				"inputs":{},
				"outputs":{},
				"debug_outputs":self.outputs
			}

		elif self.conf.variants == "score":	
			L = tf.shape(cell_outs.logprobs)[1]
			one_hot = tf.one_hot(tf.slice(self.dec_inps, [0, 1], [-1, L]), depth=self.conf.output_vocab_size, axis=-1, on_value=1.0, off_value=0.0)
			outputs = tf.reduce_sum(cell_outs.logprobs * one_hot, 2)
			outputs = tf.reduce_sum(outputs, axis=1)

			graph_nodes = {
				"loss":None,
				"inputs":{ 
					"enc_inps:0":self.enc_str_inps,
					"enc_lens:0":self.enc_lens,
					"dec_inps:0":self.dec_str_inps,
					"dec_lens:0":self.dec_lens
				},
				"outputs":{"logprobs":outputs},
				"visualize":None
			}

		else:
			L = tf.shape(cell_outs.beam_ends)[1]
			beam_symbols = cell_outs.beam_symbols
			beam_parents = cell_outs.beam_parents

			beam_ends = cell_outs.beam_ends
			beam_end_parents = cell_outs.beam_end_parents
			beam_end_probs = cell_outs.beam_end_probs
			alignments = cell_outs.alignments

			beam_ends = tf.reshape(tf.transpose(beam_ends, [0, 2, 1]), [-1, L])
			beam_end_parents = tf.reshape(tf.transpose(beam_end_parents, [0, 2, 1]), [-1, L])
			beam_end_probs = tf.reshape(tf.transpose(beam_end_probs, [0, 2, 1]), [-1, L])

			## Creating tail_ids 
			batch_size = tf.Print(batch_size, [batch_size], message="BATCH")
			batch_offset = tf.expand_dims(tf.cumsum(tf.ones([batch_size, self.beam_size], dtype=tf.int32) * self.beam_size, axis=0, exclusive=True), 2)
			offset2 = tf.expand_dims(tf.cumsum(tf.ones([batch_size, self.beam_size * 2], dtype=tf.int32) * self.beam_size, axis=0, exclusive=True), 2)

			out_len = tf.shape(beam_symbols)[1]
			self.beam_symbol_strs = tf.reshape(self.out_table.lookup(tf.cast(beam_symbols, tf.int64)), [batch_size, self.beam_size, -1])
			self.beam_parents = tf.reshape(beam_parents, [batch_size, self.beam_size, -1]) - batch_offset

			self.beam_ends = tf.reshape(beam_ends, [batch_size, self.beam_size * 2, -1])
			self.beam_end_parents = tf.reshape(beam_end_parents, [batch_size, self.beam_size * 2, -1]) - offset2
			self.beam_end_probs = tf.reshape(beam_end_probs, [batch_size, self.beam_size * 2, -1])
			self.beam_attns = tf.reshape(alignments, [batch_size, self.beam_size, out_len, -1])
			
			
			graph_nodes = {
				"loss":None,
				"inputs":{ 
					"enc_inps:0":self.enc_str_inps,
					"enc_lens:0":self.enc_lens
				},
				"outputs":{
					"beam_symbols":self.beam_symbol_strs,
					"beam_parents":self.beam_parents,
					"beam_ends":self.beam_ends,
					"beam_end_parents":self.beam_end_parents,
					"beam_end_probs":self.beam_end_probs,
					"beam_attns":self.beam_attns
				},
				"visualize":{}
			}		
		return graph_nodes 
		

	def get_init_ops(self):
		init_ops = []
		if self.conf.embedding_init:
			init_ops = [tf.variables_initializer(set(self.optimizer_params + self.global_params + self.trainable_params)- set([self.embedding]))]
			w2v = np.load(self.conf.embedding_init)
			init_ops.append(self.embedding.assign(w2v))
		else:
			init_ops = [tf.variables_initializer(set(self.optimizer_params + self.global_params + self.trainable_params))]

		if self.task_id == 0:
			vocab_file = filter(lambda x: re.match("vocab\d+\.all", x) != None, os.listdir(self.conf.data_dir))[0]
			f = codecs.open(os.path.join(self.conf.data_dir, vocab_file))
			k = [line.strip() for line in f]
			k = k[0:self.conf.output_vocab_size]
			v = [i for i in range(len(k))]
			op_in = self.in_table.insert(constant_op.constant(k), constant_op.constant(v, dtype=tf.int64))
			op_out = self.out_table.insert(constant_op.constant(v,dtype=tf.int64), constant_op.constant(k))
			init_ops.extend([op_in, op_out])
		return init_ops

	def get_restorer(self):
		var_list = self.global_params + self.trainable_params + self.optimizer_params + tf.get_default_graph().get_collection("saveable_objects")
		## Just for the FUCKING naming compatibility to tensorflow 1.1
		var_map = {}
		for each in var_list:
			name = each.name
			#name = re.sub("lstm_cell/bias", "lstm_cell/biases", name)
			#name = re.sub("lstm_cell/kernel", "lstm_cell/weights", name)
			#name = re.sub("gru_cell/bias", "gru_cell/biases", name)
			#name = re.sub("gru_cell/kernel", "gru_cell/weights", name)
			#name = re.sub("gates/bias", "gates/biases", name)
			#name = re.sub("candidate/bias", "candidate/biases", name)
			#name = re.sub("gates/kernel", "gates/weights", name)
			#name = re.sub("candidate/kernel", "candidate/weights", name)
			#name = re.sub("bias", "biases", name)
			#name = re.sub("dense/weights", "dense/kernel", name)
			#name = re.sub("dense/biases", "dense/bias", name)
			name = re.sub(":0", "", name)
			var_map[name] = each

		restorer = tf.train.Saver(var_list=var_map)
		return restorer

	def after_proc(self, out):
		if self.conf.variants == "score":
			return [{"posteriors":float(each)} for each in list(out["logprobs"])]
		else:
			outputs, probs, attns = Nick_plan.handle_beam_out(out, self.conf.beam_splits)
			outs = [[(outputs[n][i], probs[n][i]) for i in range(len(outputs[n]))] for n in range(len(outputs))]

			#sorted_outs = sorted(outs, key=lambda x:x[1]/len(x[0]), reverse=True)
			sorted_outs = [sorted(outs[n], key=lambda x:x[1], reverse=True) for n in range(len(outs))]
			after_proc_out = [[{"outputs":res[0], "probs":res[1]} for res in example] for example in sorted_outs]
			return after_proc_out 
