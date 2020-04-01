FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y software-properties-common
RUN apt-get -y install git libatlas-base-dev openmpi-bin libopenmpi-dev libnetcdf13


#RUN add-apt-repository ppa:ubuntugis/ppa && apt-get update
#RUN apt-get update
#RUN apt-get install gdal-bin -y
#RUN apt-get install libgdal-dev -y
#ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
#ENV C_INCLUDE_PATH=/usr/include/gdal

RUN apt install -y python3 python3-dev python3-pip
RUN pip3 install --upgrade setuptools
#RUN pip3 install GDAL==$(gdal-config --version)

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

#ADD . / PyRate/
#RUN cd PyRate && sed -i 's/GDAL//g' requirements.txt
#RUN pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
#RUN cd PyRate && python3 setup.py install