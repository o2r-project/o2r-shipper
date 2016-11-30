
# o2r-shipper

This is a micro service for the transmission of ERCs to external repositories.

For its role within o2r, please see [o2r-architecture](https://github.com/o2r-project/architecture).

## License

o2r-shipper is licensed under Apache License, Version 2.0, see file LICENSE. Copyright (C) 2016 - o2r project.


## Installation

    pip install -r requirements.txt

or use dockerfiles where applicable.

---

## 1. Options


shipper.py is using external API calls to manage file depositions to repository.

Required packages: ```requests```

Usage:

    python shipper.py -i INPUT_FILE_PATH -e ERC_ID -t ACCESS_TOKEN [options]


+ provide ```-i``` to specify input as absolute path to file
+ provide ```-e``` to specify o2r ERC identifier
+ provide ```-t``` to specify API access_token
+ optionally use ```-b``` to specify the API endpoint. Default is `https://sandbox.zenodo.org/api`.
+ optionally use ```-c``` to specify the calling user. If not provided, shipper will request it based on ERC id.
+ optionally use ```-d``` to specify the deposition id to work with. Leave out to create a new deposition id.
+ optionally use ```-m``` to add metadata as json file. If provided, existing metadata will be updated.
+ optionally use ```-r``` to specify a recipient repository name. Default is `zenodo`.
+ optionally use ```-x``` to enable test mode, where the newly created or specified depot will be deleted after upload.

+ use ```docker build``` command with this repository as the context to build the Docker image.

Example:

    docker build -t o2r-shipper 
    docker run --rm -v $(pwd)/o2r-shipper -i test.zip -e ERC_ID -t TOKEN -x

## 2. Answer

shipper.py return a json object containing information on the submission event:

    {
    	'compendium_id': 'AAAAA', 
    	'recipient': 'zenodo', 
    	'issuer': '0000-0000-0000-0000', 
    	'url': 'https://sandbox.zenodo.org/record/00000', 
    	'shipment_date': '2016-11-30', 
    	'deposition_id': '0000'
    }


Note that the returned record url from Zenodo will only be active after publishing.