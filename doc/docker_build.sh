#!/bin/sh

docker run -it --rm -v $(pwd):/paper -w /paper blang/latex /bin/bash
