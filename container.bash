#!/bin/bash

docker run \
     	-it \
        --rm \
        --ipc=host \
	--net host \
	--volume /dev:/dev \
	--device /dev/bus/usb \
	--device /dev/snd \
	--privileged \
	--name residencia_container \
        --volume "$PWD:/workspace" \
	--gpus all  \
	macall:riva_stream
#	pytorch/pytorch:2.3.1-cuda12.1-cudnn8-devel
