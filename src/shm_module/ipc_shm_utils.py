# -*- coding: utf-8 -*-
# @Time    : 2021/11/23 9:33
# @Author  : tk
import json
import random
# import sys
# import time
# import os
# import struct
# import copy
import struct
import multiprocessing
import traceback
from multiprocessing import Event,Condition,Process
from datetime import datetime
import numpy as np
import pickle
from .ipc_utils_func import set_logger,C_sharedata
from termcolor import colored

class SHM_manager(Process):
    def __init__(self,evt_quit,
                 signal_list,semaphore,
                 shm_name_list,
                 input_queue,
                 output_queue,
                 is_log_time,
                 idx,
                 daemon=False):
        super().__init__(daemon=daemon)
        self._logger = set_logger(colored('VENTILATOR', 'magenta'))
        self._evt_quit = evt_quit
        self._signal_list = signal_list

        self._semaphore = semaphore
        self._shm_name_list = shm_name_list

        self._input_queue = input_queue
        self._output_queue = output_queue

        self._is_log_time = is_log_time
        self.idx = idx
        # self.input_queue = multiprocessing.Manager().Queue(queue_size),
        # self.output_queue = multiprocessing.Manager().Queue(1)

    def get_input_queue(self):
        return self._input_queue

    def get_output_queue(self):
        return self._output_queue

    def get_real_data(self,buf):
        len = struct.unpack('i',buf[4:8])[0]
        d = buf[8:8+len]
        #队列不能序列化 bytes
        return pickle.loads(d)

    def run(self):
        shm_list = []
        for shm_name in self._shm_name_list:
            s_d = C_sharedata(name=shm_name,create=False)
            shm_list.append(s_d)
        task_queue1 = self._input_queue
        task_queue2 = self._output_queue

        s_d_id_list = []
        while True:
            request_id,msg = task_queue1.get()
            if self._evt_quit.is_set():
                break
            s_d_id_list.clear()
            self._semaphore.acquire()
            for i,node in enumerate(shm_list):
                flag = struct.unpack("i", node.buf[0:4])[0]
                if flag == 0:
                    s_d_id_list.append(i)
            if len(s_d_id_list) == 0:
                self._semaphore.release()
                self._logger.info('service busy  , no worker consume')
                task_queue1.put((request_id,msg))
                continue
            sel_id = random.choices(s_d_id_list)[0]
            s_d = shm_list[sel_id]

            #if isinstance(msg,dict) else msg
            # d = pickle.dumps(msg)
            # print(d)

            d = msg
            s_d.buf[4:8] = struct.pack("i", len(d))
            s_d.buf[8:8 + len(d)] = d
            s_d.buf[0:4] = struct.pack("i", 1)
            #是否信号，给其他进程
            self._semaphore.release()
            self._signal_list[sel_id].set()
            start_t = datetime.now()
            while True:
                flag = struct.unpack("i", s_d.buf[0:4])[0]
                if flag == 3:
                    break
            p_result = self.get_real_data(s_d.buf)

            s_d.buf[0:4] = struct.pack('i',0)
            task_queue2.put((request_id,p_result))
            if self._is_log_time:
                deata = datetime.now() - start_t
                micros = deata.seconds * 1000 + deata.microseconds / 1000
                self._logger.info('manager workerId {} , runtime {}'.format(sel_id, micros))

class SHM_woker(Process):
    def __init__(self,
                 evt_quit,
                 semaphore,
                 shm_name,
                 shm_size,
                 is_log_time,
                 idx,
                 group_name,
                 daemon=False):
        super().__init__(daemon=daemon)
        self._logger = set_logger(colored('VENTILATOR', 'magenta'))

        self._evt_quit = evt_quit
        self._semaphore= semaphore
        self._idx = idx
        self._group_name = group_name
        self._shm_name = shm_name

        self._s_data = C_sharedata(name=shm_name, create=True, size=shm_size)
        self._evt_signal = multiprocessing.Manager().Event()
        self._is_log_time = is_log_time

    def get_signal(self):
        return self._evt_signal

    def run_begin(self):
        raise NotImplementedError

    def run_end(self):
        raise NotImplementedError

    def run_once(self,request_data):
        raise NotImplementedError

    def run(self):
        self.run_begin()
        s_data = self._s_data
        try:
            while True :
                self._evt_signal.wait()
                if self._evt_quit.is_set():
                    break
                self._semaphore.acquire()
                flag = struct.unpack("i", s_data.buf[0:4])[0]
                if flag != 1:
                    self._semaphore.release()
                    continue
                self._evt_signal.clear()
                #工作者接收任务，修改工作标志
                s_data.buf[0:4] = struct.pack('i',2)
                self._semaphore.release()
                msg_size = struct.unpack("i", s_data.buf[4:8])[0]
                msg = s_data.buf[8:8 + msg_size]
                request_data = pickle.loads(msg)
                start_t = datetime.now()
                X = self.run_once(request_data)
                X = pickle.dumps(X)

                s_data.buf[4:8] = struct.pack("i", len(X))
                s_data.buf[8:8 + len(X)] = X
                s_data.buf[0:4] = struct.pack("i", 3)

                if self._is_log_time:
                    deata = datetime.now() - start_t
                    micros = deata.seconds * 1000 + deata.microseconds / 1000
                    self._logger.info('worker msg_size {} , runtime {}'.format(msg_size,micros))
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
        del s_data
        self.run_end()
