#!/bin/bash

# Description:
#
# The top-level run script to execute HyTools on ImgSPEC. This script accepts the inputs described in the
# algorithm_config.yaml file and pre-processes them as needed to pass into hytools/scripts/image_correct.py and/or
# hytools/scripts/trait_estimate.py. This script is currently compatible with AVIRIS Classic, AVIRIS-NG, and PRISMA
# data.
#
# Inputs:
#
# $1: URL to a trait models repository (eg. https://github.com/EnSpec/AVIRIS-C_trait_models/archive/refs/heads/main.zip)
#
# In addition to the positional arguments, this script expects downloaded radiance granules and matching reflectance
# granules to be present in a folder called "input".
#
# Also, if the user supplies an image correction config dictionary as one of the inputs then the image correction step
# will be run.  If the user supplies a trait estimate config dictionary, then the trait estimate step will be run. These
# dictionaries are passed into this script using the get_from_context.py script below.


imgspec_dir=$( cd "$(dirname "$0")" ; pwd -P )
hytools_dir=$(dirname ${imgspec_dir})

input="input"
mkdir -p output

# Activate conda environment
source activate hytools

# Get input paths for image correct
echo "Looking for input granule gzips and extracting if necessary..."
rfl_files=$(python ${imgspec_dir}/get_paths_from_granules.py -p rfl)
echo "Found input reflectance file(s): $rfl_files"
obs_ort_files=$(python ${imgspec_dir}/get_paths_from_granules.py -p obs_ort)
echo "Found input observation file(s): $obs_ort_files"

# Set ulimit according to ray recommendation
ulimit -n 8192

# Create image_correct_config
python ${imgspec_dir}/get_from_context.py image_correct_config > image_correct_config.json
echo "Created image_correct_config.json file from \"image_correct_config\" parameter"

# Check if "file_type" exists to determine if we have a non-blank image correct config
if grep -q "file_type" image_correct_config.json; then
    python $imgspec_dir/update_config.py image_correct_config.json image_correct $rfl_files $obs_ort_files
    echo "Updated image_correct_config.json with input paths and num_cpus based on number of images"

    # Execute hytools image correction
    image_correct_cmd="python $hytools_dir/scripts/image_correct.py image_correct_config.json"
    echo "Executing cmd: $image_correct_cmd"
    ${image_correct_cmd}

    # Update rfl_files to refer to corrected output paths
    # Assume corrected output file names end with either "_topo" or "_brdf"
    rfl_files_arr=()
    for file in output/*{topo,brdf}; do
        if [[ $file != *\** ]]; then
            rfl_files_arr+=("$file")
        fi
    done
    rfl_files=$(printf "%s," "${rfl_files_arr[@]}" | cut -d "," -f 1-${#rfl_files_arr[@]})
    echo "Updated rfl_files based on output of image_correct step.  Found files:"
    echo $rfl_files

else
    echo "### image_correct_config.json is empty. Not running image correction step"
fi

# Create trait_estimate_config
python ${imgspec_dir}/get_from_context.py trait_estimate_config > trait_estimate_config.json
echo "Created trait_estimate_config.json file from \"trait_estimate_config\" parameter"

trait_models_dir=""

if grep -q "file_type" trait_estimate_config.json; then
    # Download trait model repository
    trait_model_dir="trait_models"
    mkdir -p $trait_model_dir
    zip_file=$(basename $1)
    curl --retry 10 -L --output $zip_file $1
    if [[ $1 == *zip ]]; then
        unzip $zip_file -d $trait_model_dir
    fi
    if [[ $1 == *tar.gz ]]; then
        tar xvf $zip_file -C $trait_model_dir
    fi
    # Update trait_model_dir to included unzipped top-level directory name which is not known without introspection
    trait_model_dir=$(ls -d $trait_model_dir/*)
    echo "Downloaded and unzipped trait models from $1 to $trait_model_dir"

    python $imgspec_dir/update_config.py trait_estimate_config.json trait_estimate $rfl_files $obs_ort_files \
    $trait_model_dir
    echo "Updated trait_estimate_config.json with input paths, trait model paths, and num_cpus"

    # Execute hytools image correction
    trait_estimate_cmd="python $hytools_dir/scripts/trait_estimate.py trait_estimate_config.json"
    echo "Executing cmd: $trait_estimate_cmd"
    ${trait_estimate_cmd}
else
    echo "### trait_estimate_config.json is empty. Not running trait estimate step"
fi

echo "Preparing outputs (matching product types, tarring, and gzipping)..."
python ${imgspec_dir}/prepare_outputs.py output $trait_models_dir
