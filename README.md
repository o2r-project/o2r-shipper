
# o2r-shipper

This is a micro service for the transmission of ERCs to external repositories.

## License

o2r-shipper is licensed under Apache License, Version 2.0, see file LICENSE. Copyright (C) 2016 - o2r project.


## Installation

    pip install -r requirements.txt

or use dockerfiles where applicable.

---

## 1. Options


shipper.py is using external API calls to manage file depositions

Required packages: ```requests```

Usage:

    python shipper.py -i INPUT_FILE_PATH -t ACCESS_TOKEN [-m MD -b BASE_URL_API -d ID -x]


+ use ```-i``` to specify input as absolute path to file
+ use ```-t``` to specify API access_token
+ optionally use ```-m``` to add metadata as json. It this argument is provided existing metadata will be updated.
+ optionally use ```-b``` to specify the API endpoint. Default is `https://sandbox.zenodo.org/api`.
+ optionally use ```-d``` to specify the deposition id to work with. Leave out to create a new deposition id.
+ optionally use ```-x``` to enable test mode, where the newly created or specified depot will be deleted after upload.

+ use ```docker build``` command with this repository as the context to build the Docker image.

Example:

    docker build -t o2r-shipper 
    docker run --rm -v $(pwd)/o2r-shipper -i test.zip -t TOKEN -x
