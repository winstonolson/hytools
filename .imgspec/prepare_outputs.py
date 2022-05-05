#! /usr/bin/python

import glob
import json
import os
import shutil
import subprocess
import sys


def main():
    output_dir = sys.argv[1]

    print(f"Preparing output directory {output_dir} ")

    # Figure out unique scenes
    output_prefixes = None
    output_files = [os.path.basename(f) for f in glob.glob(f"{output_dir}/*")]
    if output_files is None or len(output_files) == 0:
        print("Could not find any output files in the output folder. Exiting...")
        sys.exit(1)

    # Match based on filename
    if output_files[0].startswith("f"):
        # AVIRIS Classic
        output_prefixes = set([f[:16] for f in output_files])
    elif output_files[0].startswith("ang"):
        # AVIRIS-NG
        output_prefixes = set([f[:18] for f in output_files])
    elif output_files[0].startswith("PRS"):
        # PRISMA
        output_prefixes = set([f[:38] for f in output_files])

    if output_prefixes is None or len(output_prefixes) == 0:
        print("Could not find any matching output prefixes for known instruments in the output folder. Exiting...")
        sys.exit(1)

    # Loop through prefixes to handle case where there are multiple scenes (grouped mode)
    for prefix in output_prefixes:
        # Match topo, brdf, glint
        crfl_files = [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*topo")]
        crfl_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*topo.hdr")]
        crfl_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*brdf")]
        crfl_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*brdf.hdr")]
        crfl_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*glint")]
        crfl_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*glint.hdr")]
        # Create folder for product, then move and rename files
        product_dir = f"{prefix}_crfl"
        os.makedirs(os.path.join(output_dir, product_dir))
        for file in crfl_files:
            if file.endswith(".hdr"):
                shutil.move(f"{output_dir}/{file}", os.path.join(output_dir, product_dir, f"{prefix}_crfl.hdr"))
            else:
                shutil.move(f"{output_dir}/{file}", os.path.join(output_dir, product_dir, f"{prefix}_crfl"))
        # Tar and gzip, then remove product dir
        subprocess.run(f"cd {output_dir}; tar czvf {product_dir}.tar.gz {product_dir}; rm -rf {product_dir}",
                       shell=True)

        # Match trait maps
        if len(sys.argv) > 2 and len(sys.argv[2]) > 0:
            trait_models_dir = sys.argv[2]
            trait_files = glob.glob(os.path.join(trait_models_dir, "*.json"))
            trait_names = []
            for file in trait_files:
                # Read trait names from files
                with open(file, "r") as f:
                    config = json.load(f)
                    trait_names.append(config["name"])

            # Loop through trait names, and match files
            for trait_suffix in trait_names:
                trait_files = [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*{trait_suffix}")]
                trait_files += [os.path.basename(f) for f in glob.glob(f"{output_dir}/{prefix}*{trait_suffix}.hdr")]
                if len(trait_files) == 0:
                    continue
                # Reformat trait suffix to lowercase and to remove spaces, underscores, and dashes
                suffix = trait_suffix.lower().replace(" ", "").replace("_", "").replace("-", "")
                # Create folder for product, then move and rename files
                product_dir = f"{prefix}_{suffix}"
                os.makedirs(os.path.join(output_dir, product_dir))
                for file in trait_files:
                    if file.endswith(".hdr"):
                        shutil.move(f"{output_dir}/{file}", os.path.join(output_dir, product_dir,
                                                                         f"{prefix}_{suffix}.hdr"))
                    else:
                        shutil.move(f"{output_dir}/{file}", os.path.join(output_dir, product_dir, f"{prefix}_{suffix}"))
                # Tar and gzip, then remove product dir
                subprocess.run(f"cd {output_dir}; tar czvf {product_dir}.tar.gz {product_dir}; rm -rf {product_dir}",
                               shell=True)


if __name__ == "__main__":
    main()
