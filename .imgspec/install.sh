#!/bin/bash

# Install script for hytools - currently just runs pip install

set -x

# Define some useful directories
imgspec_dir=$( cd "$(dirname "$0")" ; pwd -P )
hytools_dir=$(dirname ${imgspec_dir})

# Install unzip
apt install -y unzip

# Create conda env
conda create -n hytools -y -c conda-forge python=3.7
source activate hytools

# Run pip install in developer mode
cd $hytools_dir
pip install -e .
