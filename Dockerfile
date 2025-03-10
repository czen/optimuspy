FROM ubuntu:latest

RUN mkdir optimuspy

COPY . optimuspy

WORKDIR /optimuspy

RUN apt update
RUN apt install g++ clang-15 make \
    exuberant-ctags xz-utils python3-pip -y

RUN sh scripts/rabbitmq.sh

WORKDIR /optimuspy/opsc-bin

RUN tar xf opsc.tar.xz
RUN mv lib/* /usr/local/lib/
RUN mv opsc /optimuspy/opsc
RUN rmdir lib

WORKDIR /optimuspy/opsc
RUN chmod +x opsc
RUN ldconfig

WORKDIR /optimuspy/catch2
# RUN curl -O https://github.com/catchorg/Catch2/releases/download/v3.3.2/catch_amalgamated.cpp
# RUN curl -O https://github.com/catchorg/Catch2/releases/download/v3.3.2/catch_amalgamated.hpp
RUN make gpp
RUN make clang

WORKDIR /optimuspy
RUN pip3 install -r requirements/prod.txt
RUN python3 ./manage.py migrate
RUN mkdir -p tasks
RUN rm -rf /var/cache/apt/archives /var/lib/apt/lists/*
EXPOSE 8000
