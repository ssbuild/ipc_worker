# @Time    : 2021/11/26 21:15
# @Author  : tk
# @FileName: zmq_utils.py
import json

import zmq
import time
import uuid
from collections import namedtuple
# from queue import Queue
from multiprocessing import Queue
from multiprocessing import Event,Process
from threading import Lock
from ..utils import set_logger
from termcolor import colored
import pickle
from datetime import datetime
from .ipc_utils_func import auto_bind




class ZMQ_worker(Process):
    def __init__(self,identity,group_name,evt_quit,is_log_time,idx,daemon=False):
        super(ZMQ_worker,self).__init__(daemon=daemon)

        self._logger = set_logger(colored('VENTILATOR', 'magenta'))

        self.__identity = identity
        self._group_name = group_name
        self._evt_quit = evt_quit
        self._idx = idx
        self._is_log_time = is_log_time


        self.signal = Event()

        self.__is_closed = False


    def _set_addr(self,addr_sink,addr_pub):
        self._addr_sink = addr_sink
        self._addr_pub = addr_pub

    # Process begin trigger this func
    def run_begin(self):
        raise NotImplementedError

    # Process end trigger this func
    def run_end(self):
        raise NotImplementedError

    # any data put will trigger this func
    def run_once(self, request_data):
        raise NotImplementedError

    def __processinit__(self):
        self._context = zmq.Context()
        # 消费者 接收代理 数据
        self._receiver = self._context.socket(zmq.SUB)
        self._receiver.setsockopt(zmq.SUBSCRIBE, self.__identity)
        # self._receiver.setsockopt(zmq.SUBSCRIBE, b'')

        # self._receiver.connect('tcp://{}:{}'.format(self._ip, self._port))
        self._receiver.connect(self._addr_pub)

        # 结果推送
        self._sender = self._context.socket(zmq.PUSH)
        self._sender.setsockopt(zmq.LINGER, 0)
        # self._sender.connect('tcp://{}:{}'.format(self._ip, self._port_out))
        self._sender.connect(self._addr_sink)

    def close(self):
        if not self.__is_closed:
            self.__is_closed = True
            self._receiver.close()
            self._sender.close()
            self._context.term()

    def run(self):
        self.__processinit__()
        self.signal.set()

        self.run_begin()
        while not self._evt_quit.is_set():
            _,msg,b_request_id = self._receiver.recv_multipart()
            msg_size = len(msg)
            request_data = pickle.loads(msg)
            start_t = datetime.now()
            X = self.run_once(request_data)
            X = pickle.dumps(X)
            self._sender.send_multipart([b_request_id,X])
            if self._is_log_time:
                deata = datetime.now() - start_t
                micros = deata.seconds * 1000 + deata.microseconds / 1000
                self._logger.info('worker msg_size {} , runtime {}'.format(msg_size, micros))
        self.close()
        self.run_end()








class ZMQ_sink(Process):
    def __init__(self,queue_size,group_name,evt_quit,daemon=False):
        super(ZMQ_sink,self).__init__(daemon=daemon)

        self.logger = set_logger(colored('VENTILATOR', 'magenta'))

        self.group_name = group_name

        self.is_closed = False
        self.evt_quit = evt_quit
        self.pending_request = set()
        self.pending_response = {}
        self.queue = Queue(maxsize=queue_size)
        #
        self.locker = Lock()
        self.signal = Event()
        self.addr = None
    def wait_init(self):
        self.addr = self.queue.get()

    def get(self,request_id):
        response = None
        while True:
            is_end = False
            self.signal.wait(0.01)
            self.locker.acquire(blocking=False)
            if request_id in self.pending_request:
                if request_id in self.pending_response:
                    response = self.pending_response.pop(request_id)
                    self.pending_request.remove(request_id)
                    self.signal.clear()
                    is_end = True
                else:
                    r_id,response = self.queue.get()
                    if r_id != request_id:
                        self.pending_response[r_id] = response
                    else:
                        is_end = True
            else:
                self.logger.error('bad request_id {}'.format(request_id))
                is_end = True
            self.locker.release()
            if is_end:
                break
        return response

    def __processinit__(self):
        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.setsockopt(zmq.LINGER, 0)
        # self.receiver.bind('tcp://*:{}'.format(self.port_out))
        self.addr = auto_bind(self.receiver)
        self.logger.info('group {} sink bind {}'.format(self.group_name,self.addr))
        self.queue.put(self.addr)

    def close(self):
        if not self.is_closed:
            self.is_closed = True
            self.receiver.close()
            self.context.term()

    def run(self):
        self.__processinit__()

        while not self.evt_quit.is_set():
            request_id,response = self.receiver.recv_multipart()
            r_id = int.from_bytes(request_id, byteorder='little', signed=False)
            self.queue.put((r_id,response))
            self.signal.set()

        self.close()


    def add_request_id(self,request_id):
        self.locker.acquire()
        self.pending_request.add(request_id)
        self.locker.release()



class ZMQ_manager(Process):
    def __init__(self,idx,queue_size,group_name,evt_quit,daemon=False):
        super(ZMQ_manager, self).__init__(daemon=daemon)

        self.logger = set_logger(colored('VENTILATOR', 'magenta'))
        self.group_name = group_name
        self.request_id = 0
        self.idx = idx

        self.queue = Queue(queue_size)
        self.evt_quit = evt_quit
        self.locker = Lock()
        self.addr = None
        self.is_closed = False

    def wait_init(self):
        self.addr = self.queue.get()

    def put(self,identity,msg):
        self.locker.acquire()
        self.request_id += 1
        request_id = self.request_id
        self.locker.release()
        self.queue.put((request_id,identity,msg))
        return request_id

    def __processinit__(self):
        self.context = zmq.Context()
        self.sender = self.context.socket(zmq.PUB)
        self.sender.setsockopt(zmq.LINGER, 0)
        # self.sender.bind('tcp://*:{}'.format(self.port))
        self.addr = auto_bind(self.sender)
        self.queue.put(self.addr)
    def close(self):
        if not self.is_closed:
            self.is_closed = True
            self.sender.close()
            self.context.term()

    def run(self):
        self.__processinit__()
        self.logger.info('group {} manager bind {}'.format(self.group_name,self.addr))
        while not self.evt_quit.is_set():
            request_id,identity,msg = self.queue.get()
            self.sender.send_multipart([identity,msg, request_id.to_bytes(4,byteorder='little',signed=False)])

        self.close()


