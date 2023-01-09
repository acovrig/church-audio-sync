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

ADD Makefile compute* sound* requirements.txt /src/

RUN pip3 install -r requirements.txt
RUN make clean && make -j

ADD . /src
