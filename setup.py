# -*- coding:utf-8 -*-
import setuptools
import sys
import platform
import os
import shutil

from setuptools import Extension,find_packages

package_list = find_packages('src')

packge_list = find_packages('src')
package_dir= {'ipc_worker.' + k : 'src/' + k.replace('.','/') for k in packge_list }
package_dir.update({'ipc_worker': 'src'})


def get_desc():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    def load_file(demo_file):
        with open(demo_file,mode='r',encoding='utf-8') as f:
            data_string = str(f.read())
        return data_string

    data_string = 'support share memory (py>=3.8 and linux) and mq process worker (py >=3.6)\n'
    long_description_str = '```py' + '\n' + data_string + '\n' + '```' + '\n'


    data_string = load_file(os.path.join(current_dir,'test_shm_ipc.py'))


    long_description_str += '```py' + '\n' + data_string + '\n'+ '```' + '\n'

    data_string = load_file(os.path.join(current_dir, 'test_zmq_ipc.py'))
    long_description_str += '```py' + '\n' + data_string + '\n' + '```' + '\n'

    return long_description_str

title = 'ipc-worker: Inter-Process Communication , muti Process Woker works by share memory or MQ.'
current_dir = os.path.dirname(os.path.abspath(__file__))
platforms_name = sys.platform + '_' + platform.machine()




if __name__ == '__main__':


    setuptools.setup(
        platforms=platforms_name,
        name="ipc-worker",
        version="0.0.9",
        author="ssbuild",
        author_email="9727464@qq.com",
        description=title,
        long_description_content_type='text/markdown',
        long_description= title + '\n\n' + get_desc(),
        url="https://github.com/ssbuild",
        #packages=setuptools.find_packages(exclude=['setup.py']),
        packages=list(package_dir.keys()),   # 指定需要安装的模块
        include_package_data=True,
        package_dir=package_dir,
        package_data={'': ['*.pyd','*.so','*.dat','*.h','*.c','*.java','.__data__.pys','.__meta__.pys']},
        #ext_modules=[PrecompiledExtesion('ipc_worker')],
        install_requires=[], # 指定项目最低限度需要运行的依赖项
        python_requires='>=3, <4', # python的依赖关系
        #install_requires=['numpy>=1.18.0'],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Education',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: C++',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Mathematics',
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Topic :: Software Development',
            'Topic :: Software Development :: Libraries',
            'Topic :: Software Development :: Libraries :: Python Modules',
        ],
        license='Apache 2.0',
        keywords=["ipc-worker","ipc_worker","ipc","process worker","ipc","ipc mq","fast-ipc","process ipc",
                  ],
    )
