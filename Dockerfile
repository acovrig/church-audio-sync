FROM ubuntu:latest
RUN mkdir /src
WORKDIR /src
# ENTRYPOINT "./compute-sound-offset.sh"
ENTRYPOINT ["python3", "entrypoint.py"]

RUN apt update \
  && apt install -y \
    bc \
    build-essential \
    ffmpeg \
    libfftw3-dev \
    libsndfile1-dev \
    python3 \
    python3-pip \
    sox \
  && apt clean

RUN pip3 install autosub3

ADD Makefile compute* sound* /src/
RUN make clean && make -j

ADD . /src
