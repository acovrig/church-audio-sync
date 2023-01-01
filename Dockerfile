FROM ubuntu:latest
RUN mkdir /src
WORKDIR /src
ENTRYPOINT ["python3", "/src/entrypoint.py"]

RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
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
