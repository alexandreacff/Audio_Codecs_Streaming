#!/bin/bash

docker run \
     	-it \
        --rm \
        --ipc=host \
	--net host \
	--volume /dev:/dev \
	--privileged \
	--name residencia_container \
        --volume "$PWD:/workspace" \
	--gpus all  \
	pytorch/pytorch:2.3.1-cuda12.1-cudnn8-devel
