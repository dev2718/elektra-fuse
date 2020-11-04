# run this container with any of the run scripts (in order to mount the source code folder, ensure privileged mode to be able to mount fuse, setup logging to nohup.out/stdout)

FROM ubuntu:focal 

RUN apt-get update

#install everything for fuse
RUN apt-get -y install libfuse-dev fuse python3-pip
RUN pip3 install fusepy

#convinience
RUN apt-get -y install vim less tree xattr jp2a wget 

#setting timezone so that configuring tzdata can happen non-interactively
ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/time

#install electra from debian packages

WORKDIR /root

RUN wget https://build.libelektra.org/job/libelektra-release/70/artifact/artifacts/ubuntu-focal/ubuntu-focal-release.tar.gz
RUN tar -xf ubuntu-focal-release.tar.gz
RUN mv home/jenkins/workspace/libelektra-release/0.9.3/debian/0.9.3-1/ packages
RUN rm -r home
RUN dpkg -i ./packages/*.deb || true
RUN apt-get -y -f install
RUN dpkg -i ./packages/*.deb || true
RUN apt-get -y -f install
RUN rm -r packages ubuntu-focal-release.tar.gz


#create mountpoint
RUN mkdir /root/mount

#copy source
COPY src /root/src
