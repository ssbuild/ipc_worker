# -*- coding: utf-8 -*-
# @Time    : 2021/11/29 9:57
# @Author  : tk
import os
import uuid
import zmq

def auto_bind(socket):
    # socket.bind_to_random_port('tcp://127.0.0.1')
    # return socket.getsockopt(zmq.LAST_ENDPOINT).decode('ascii')

    if os.name == 'nt':  # for Windows
        socket.bind_to_random_port('tcp://127.0.0.1')
    else:
        # Get the location for tmp file for sockets
        try:
            tmp_dir = os.environ['ZEROMQ_SOCK_TMP_DIR']
            if not os.path.exists(tmp_dir):
                raise ValueError('This directory for sockets ({}) does not seems to exist.'.format(tmp_dir))
            tmp_dir = os.path.join(tmp_dir, str(uuid.uuid1())[:8])
        except KeyError:
            tmp_dir = '*'

        socket.bind('ipc://{}'.format(tmp_dir))
    return socket.getsockopt(zmq.LAST_ENDPOINT).decode('ascii')