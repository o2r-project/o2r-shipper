[![](https://images.microbadger.com/badges/image/o2rproject/o2r-shipper.svg)](https://microbadger.com/images/o2rproject/o2r-shipper "Get your own image badge on microbadger.com")

# o2r-shipper

This is a micro service for the transmission of ERCs to external repositories.

For its role within o2r, please see [o2r-architecture](https://github.com/o2r-project/architecture).

## License

o2r-shipper is licensed under Apache License, Version 2.0, see file LICENSE. Copyright (C) 2016, 2017 - o2r project.

## Installation

    pip install -r requirements.txt

or use the Dockerfile.

---

## 1. Options for the shipper service

shipper.py is using external API calls to manage file depositions to repositories while contributing shipment api routes for the o2r web api.

Required packages: ```requests```, ```bottle```, ```pymongo```, ```wsgi-request-logger```

Usage:

    python shipper.py -t {ACCESS_TOKENS}

+ optionally use ```-t``` to specify API access_tokens (e.g. Zenodo API key).
The received argument must be a valid JSON, e.g. `{\"my_repo\": \"my_key\"}`.
This argument will be preferred, even if there is are tokens available through configuration (s. below).

+ use ```docker build``` command with this repository as the context to build the Docker image.

Example:

    docker build -t o2r-shipper
    docker run --rm -v $(pwd)/o2r-shipper -t {ACCESS_TOKENS}

## 2. Endpoint at o2r web API:

Please refer to the documentation available at:

+ [o2r-web-api](http://o2r.info/o2r-web-api/shipment/)
+ [[dev] o2r-web-api shipments](https://github.com/o2r-project/o2r-web-api/blob/master/docs/shipment.md)


## 3. Configuration

Configuration is based on environment variables as shown in the table below. The defaults are entries in the `config.json` file, which must be in the same directory as `shipper.py`, and can also be changed in that file.

**ENV VAR** | **config file** | **description**
------ | ------ | ------
`SHIPPER_MONGODB` | `mongodb_host` | MongoDB connection string, including protocol, host and port, default is `mongodb://localhost:27017/`
`SHIPPER_MONGO_NAME` | `mongodb_db` | name of the MongoDB
`SHIPPER_BOTTLE_HOST` | `bottle_host` | host for bottle, the WSGI micro web-framework used with shipper; default is `localhost`, to allows access from other local services running in containers, set this to `0.0.0.0`
`SHIPPER_BOTTLE_PORT` | `bottle_port` | port for bottle
`SHIPPER_REPO_TOKENS` | `repository_tokens` | IDs and API tokens for the repos
`SHIPPER_BASE_PATH` | `base_path` | base path of target compendium
`SHIPPER_MAX_DIR_SIZE` | `max_size_mb` | dir size limit for transmission
`SHIPPER_SECRET` | `session_secret` | session secret for the o2r platform
`SHIPPER_USERLEVEL_MIN` | `userlevel_min` | user level needed to do shipments

---

## Shipment recipients ("Repos")

New repositories that serve as shipping destinations can be added to the `/repo` folder of the shipper. They  wrap the API of the target repository. Their filename must start with `repo` and their classname must start with `RepoClass` in order to be recognized. Moreover each repo provides an ID, a LABEL and a HOST in its configuration as well as functions to return these values. The repo classes currently avaiable in that directory can serve as extensive examples.

### Eudat b2share repository

To ship ERC to [Eudat b2share](https://b2share.eudat.eu/) (or the [Eudat b2share Sandbox](https://trng-b2share.eudat.eu/)), you must create an account and log in.
Then go to your account and get the personal access token.

### Zenodo repository

To ship ERC to [Zenodo](https://zenodo.org) (or the [Zenodo Sandbox](https://sandbox.zenodo.org)), you must create an account and log in.
Then go to your account _Settings_, open the _Applications_ settings and add a new _Personal access token_ including the scopes `deposit:write` and `deposit:actions`.
