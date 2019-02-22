#!/bin/bash

./main.py "$1" | tee out && diff ref out
