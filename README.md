# Workshop
----
[![Powered by Tensorflow](https://www.tensorflow.org/_static/images/tensorflow/logo.png)](https://www.tensorflow.org/)

# Description
#### This is a tensorflow workshop to develop, train, test, serve and deploy models. 
Typically we first develop a customized model by inheriting from the basic ModelCore class we offered, then add parameters configuration before we started a training thread. As the training proceeds, we supervise the training process through tensorboard in order to detect any possible errors at the first time. We can pause, continue or stop the training threads as we wish. After some epochs, the Test module is used to judge if the model is well trained. When the training is done, we export the checkpoints to produce an out-of-box model that can be loaded by tensorflow-serving.
    
  - [Requirements](#requirements)
  - [Resources](#resources)
    - [Machines](#machines)
    - [Data](#data)
  - [Training](#training)
    - [Build models](#build-models)
    - [Creating training threads](#creating-training-threads)
    - [Managing training threads](#managing-training-threads)
  - [Testing](#testing)
    - [Command-line testing](#command-line-testing)
    - [Batch testing](#batch-testing)
  - [Serving](#serving)
    - [Build customized servers](#build-customized-servers)
    - [Deploying servers](#deploying-servers)

# Requirements
### tensorflow(python)
### tensorflow-serving
### tensorboard
### tornado
### multitail
### expect

# Resources
Resuources include machines(gpus), origin corpus, data-processing scripts and some preprocessed training data.

### Machines
There are two groups of machines one for ***offline development/traing***, another for ***online serving***, which are listed here with gpu type name:GPU_CORExNUM:

For offline development and training(currently):
```shell
    ssh Nick@10.141.104.69  # GPU_m40x8, passwd:Nick; Nick is a sudoer here, u can also use root, but don't forget the .bashrc file under ~/;
                            # A machine for main development that folked TFWorkshop, tensorflow/tensorflow-serving built here by bazel;
                            # A part of training data here.
    
    ssh root@10.141.176.103 # GPU_p40x8; passwd:chatbot@2017; Another machine for main development, also folked TFWorkshop;
                            # Another part of data for training here.
    
    ssh root@10.141.105.100 # GPU_k40x4; passwd:chatbot@2017; Currently used by interns;
    ssh root@10.141.105.106 # GPU_k40x4; passwd:chatbot@2017; Sometimes also used for online serving, under a nginx agent.
```

For online serving(currently):
```shell
    # All GPU_m40x2;
    # Passwd:chatbot@2017online
    ssh root@10.153.50.79
    ssh root@10.153.50.80
    ssh root@10.153.50.81
    ssh root@10.153.50.82
    ssh root@10.153.50.83
    ssh root@10.153.50.84
    ssh root@10.153.58.66
    ssh root@10.153.58.67
```
> Note that there are still a little more gpus held by other person not listed here. Ask Duyi :-)

### Data
Please refer to [DataSet] for detailed description

# Training
We provided highly generalized base class with other utils and components to build reliable model easily in `models/`. We Provide a group of scripts to conduct and control training tasks.

```sh
    $ ssh root@10.141.176.103 # passwd: chatbot@2017
    
    @nmyjs_176_103 ~]# gogenerate
    @nmyjs_176_103 GenerateWorkshop]# ls
    all_up.sh  data  env  job.sh  models  online.sh  README.md  runtime  servers  test_data  test.py  Test.py  test_res  workshop.py
    
```
### Build models
### Creating training threads
### Managing training threads

# Testing
### Command-line testing
### Batch testing

# Serving
A model server is typically composed of three parts:
* A server configuration defined in `SERVICE_SCHEDULES` in `service_schedules.py`
* Some back-end *tensorflow-servings* each of which loads an out-of-box-format model that might be exported from some checkpoint
files(or just copied from somewhere or generated during training, whatever) according to what is defined in `service_schedules.py`.
* A front-end tornado based server to handle basic asynchronous/parallel issues and some dispatching or some task-specific logics

### Build customized servers


### Deploying servers


| Params| usage |
| ------ | ------ |
| index_type | Indexing system name, u may use others (e.g. searchhub -- used many thousands of years ago, refer to searchhub_candidates(), currently we use 'elastic' |
| index_name | *chaten_brokesisters3* for current example, and u may change it according to how u inject data |
| data_type | *data_brokesisters3_1* for current examnple, also may be altered as u inject data with a different sub_name|
| procnum | process number, **note that they will not share memory !**|
| score_host | scorer server addr, currently *http://10.141.176.103:9011*|
| elastic_host | elastic_host server, currently *http://10.152.72.238:9200*|



   [DataSet]: <https://git.sogou-inc.com/intelligent-dialogue/Datasets.git>