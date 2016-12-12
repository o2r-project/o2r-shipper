
# o2r-shipper

This is a micro service for the transmission of ERCs to external repositories.

For its role within o2r, please see [o2r-architecture](https://github.com/o2r-project/architecture).

## License

o2r-shipper is licensed under Apache License, Version 2.0, see file LICENSE. Copyright (C) 2016 - o2r project.


## Installation

    pip install -r requirements.txt

or use the Dockerfile.

---

## 1. Options for the shipper service


shipper.py is using external API calls to manage file depositions to repository.

Required packages: ```requests```

Usage:

    python shipper.py -i INPUT_FILE_PATH -e ERC_ID -t ACCESS_TOKEN [options]


+ provide ```-t``` to specify API access_token
+ optionally use ```-x``` to enable test mode, where the newly created or specified depot will be deleted after upload.

+ use ```docker build``` command with this repository as the context to build the Docker image.

Example:

    docker build -t o2r-shipper 
    docker run --rm -v $(pwd)/o2r-shipper -i test.zip -e ERC_ID -t TOKEN -x



## 2. Endpoint at o2r web API:

Please refer to the documentation available at: 

+ [https://github.com/o2r-project/o2r-web-api/blob/master/docs/shipment.md](https://github.com/o2r-project/o2r-web-api/blob/master/docs/shipment.md) 
+ [http://o2r.info/o2r-web-api/shipment/](http://o2r.info/o2r-web-api/shipment/)




## 3. Configuration

Can be done with environment vars and defaults to entries in `config.json` file that must be in the same directory as `shipper.py`.

**ENV VAR** | **config file** | **description**
------ | ------ | ------
`SHIPPER_MONGODB` | `mongodb_host` | host for the mongo db
`SHIPPER_MONGO_NAME` | `mongodb_db` | name of the mongo db
`SHIPPER_BOTTLE_HOST` | `bottle_host` | host for bottle, the WSGI micro web-framework used with shipper
`SHIPPER_BOTTLE_PORT` | `bottle_port` | port for bottle
`SHIPPER_REPO_ZENODO_HOST` | `repository_zenodo_host` | host of zenodo's API
`SHIPPER_BASE_PATH` | `SHIPPER_BASE_PATH` | base path of target compendium
`SHIPPER_MAX_DIR_SIZE` | `max_size_mb` | dir size limit for transmission
`SHIPPER_SECRET` | `session_secret` | session secret
`SHIPPER_USERLEVEL_MIN` | `userlevel_min` | user level needed to do shipments
