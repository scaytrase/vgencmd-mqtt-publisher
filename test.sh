#!/bin/env bash

export $(grep -v '^#' test.env | xargs)

python3 publisher.py