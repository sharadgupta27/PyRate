FROM ubuntu:bionic
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y
RUN apt install pkg-config gcc wget build-essential libssl-dev zlib1g-dev libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev libffi-dev -y

# install Python 3.7.4
RUN wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tgz && \
tar -zxf Python-3.7.4.tgz && \
cd Python-3.7.4 && \
./configure && \
nproc | xargs -I % make -j% && \
make install && \
ln -s /usr/local/bin/python3.7 /usr/bin/python

RUN apt install sqlite3
### install Proj 6.2.1
RUN wget https://download.osgeo.org/proj/proj-6.2.1.tar.gz && tar -zxf proj-6.2.1.tar.gz && cd proj-6.2.1 && ./configure && nproc | xargs -I % make -j% && make install
#
## install jasper
RUN apt-get install jasper -y
#wget http://security.ubuntu.com/ubuntu/pool/main/j/jasper/libjasper-dev_1.900.1-debian1-2.4ubuntu1.2_amd64.deb
#wget http://security.ubuntu.com/ubuntu/pool/main/j/jasper/libjasper1_1.900.1-debian1-2.4ubuntu1.2_amd64.deb
#sudo apt-get install ./libjasper-dev_1.900.1-debian1-2.4ubuntu1.2_amd64.deb ./libjasper1_1.900.1-debian1-2.4ubuntu1.2_amd64.deb

#RUN yum install -y yum-utils epel-release
#RUN yum-config-manager --enable epel
#RUN yum install -y hdf5-devel
#
#RUN yum-config-manager --enable epel
#RUN yum install -y netcdf-devel
#
## install GDAL 3.0.2
RUN wget https://download.osgeo.org/gdal/3.0.2/gdal-3.0.2.tar.gz && tar -zxf gdal-3.0.2.tar.gz && cd gdal-3.0.2 && ./configure && nproc | xargs -I % make -j% && make install
#
## install open-mpi 2.1.6
RUN wget https://download.open-mpi.org/release/open-mpi/v2.1/openmpi-2.1.6.tar.gz && tar -zxf openmpi-2.1.6.tar.gz && cd openmpi-2.1.6 && ./configure && nproc | xargs -I % make -j% && make install
#
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
#
RUN echo '/usr/local/lib' >> /etc/ld.so.conf
RUN ldconfig
ADD . / PyRate/
RUN cd PyRate && python3 setup.py install
RUN pip3 uninstall GDAL -y
RUN pip3 install GDAL==$(gdal-config --version)
RUN cd PyRate && pytest tests/