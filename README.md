[![](https://images.microbadger.com/badges/image/o2rproject/o2r-shipper.svg)](https://microbadger.com/images/o2rproject/o2r-shipper "Get your own image badge on microbadger.com")

# o2r-shipper

This is a micro service for the transmission of ERCs to external repositories.

For its role within o2r, please see [o2r-architecture](https://github.com/o2r-project/architecture).

## License

o2r-shipper is licensed under Apache License, Version 2.0, see file LICENSE. Copyright (C) 2016, 2017 - o2r project.

## Installation

    pip install -r requirements.txt

_or use the Dockerfile_.

---

## 1. Options for the shipper service

shipper.py is using external API calls to manage file depositions to repositories while contributing shipment api routes for the o2r web api.

Usage:

    python shipper.py -t {ACCESS_TOKENS}

+ use ```-t``` to specify API access_tokens (e.g. Zenodo API key).
The received argument must be a valid JSON, e.g. `{\"my_repo\": \"my_key\"}`.
This argument will be preferred, even if there are tokens available through configuration (s. below).

+ optionally use ```-d``` to enable debug mode and increase verbosity upon error.

+ use ```docker build``` command with this repository as the context to build the Docker image.

Example:

    docker build . -t o2r-shipper
    docker run --rm -v $(pwd)/o2r-shipper -t {ACCESS_TOKENS}

## 2. Endpoint at o2r API

Please refer to the documentation available at:

+ [o2r API](https://o2r.info/api/shipment/)
+ [[dev] o2r-web-api shipments](https://github.com/o2r-project/o2r-web-api/blob/master/docs/shipment.md)

## 3. Configuration

Configuration is based on environment variables as shown in the table below. The defaults are entries in the `config.json` file, which must be in the same directory as `shipper.py`, and can also be changed in that file.

**ENV VAR** | **config file** | **description**
------ | ------ | ------
`SHIPPER_MONGODB` | `mongodb_host` | MongoDB connection string, including protocol, host and port, default is `mongodb://localhost:27017/` (note the trailing slash)
`SHIPPER_MONGO_NAME` | `mongodb_db` | name of the MongoDB, default is `muncher`
`SHIPPER_BOTTLE_HOST` | `bottle_host` | host for bottle, the WSGI micro web-framework used with shipper; default is `localhost`, to allows access from other local services running in containers, set this to `0.0.0.0`
`SHIPPER_BOTTLE_PORT` | `bottle_port` | port for bottle, defaults to `8087`
`SHIPPER_REPO_TOKENS` | `repository_tokens` | IDs and API tokens for the repositories
`SHIPPER_BASE_PATH` | `base_path` | base path of target compendium
`SHIPPER_MAX_DIR_SIZE` | `max_size_mb` | dir size limit for transmission
`SHIPPER_SECRET` | `session_secret` | session secret used by the o2r microservices
`SHIPPER_USERLEVEL_MIN` | `userlevel_min` | user level needed to do shipments

---


## Bagit Validity

At shipping, the shipper attempts to validate the target files as valid bagit bags, using the LoC bagit.py module. If no bagit bag is found, it is created.
An invalid or bag will be updated. The shipper is designed to transport only valid bags to its recipients.

## Shipment recipients ("Repos")

New repositories that serve as shipping destinations can be added to the `/repo` folder of the shipper. They wrap the API of the target repository. Their filename must start with `repo` and their class name must start with `RepoClass` in order to be recognized. Moreover each repo provides an ID, a LABEL and a HOST in its configuration as well as functions to return these values. They inherit necessary imports from the master `repoclass` module found in the same folder. 
The repo classes currently available in that directory can serve as extensive examples.

## Supported 3rd party repositories

### Download as repository surrogate
_ID_ `download`

In order to "ship to your own storage", there is a download repoclass available, that unlike the remote repositories creates a download link for streaming the targeted compendium.

### Eudat b2share (sandbox) repository
_IDs_ `b2share_sandbox`, `b2share`

To ship ERC to [Eudat b2share](https://b2share.eudat.eu/) (or the [Eudat b2share Sandbox](https://trng-b2share.eudat.eu/)), you must create an account and log in.
Then go to your account and get the personal access token.

### Zenodo (sandbox) repository
_IDs_ `zenodo_sandbox`, `zenodo`

To ship ERC to [Zenodo](https://zenodo.org) (or the [Zenodo Sandbox](https://sandbox.zenodo.org)), you must create an account and log in.
Then go to your account _Settings_, open the _Applications_ settings and add a new _Personal access token_ including the scopes `deposit:write` and `deposit:actions`.

## Testing

Tests are implemented using [pytest](https://pytest.org) following [its conventions for test discovery](https://docs.pytest.org/en/latest/goodpractices.html#test-discovery).
Configuration file is `pytest.ini`.

### Manual testing

The tests require a running shipper service including the required database.
The shipper may run in a container.
The following example configures only the `download` repository.

```bash
pip install -U pytest requests json

# start shipper in container and database:
docker build -t shipper .
docker run --name testdb -d -p 27017:27017 mongo:3.4
docker run --name testshipper -t -d -p 8087:8087 --link testdb:testdb -e SHIPPER_MONGODB=mongodb://testdb:27017 -e SHIPPER_BOTTLE_HOST=0.0.0.0 -e SHIPPER_REPO_TOKENS='{"download": ""}' shipper
sleep 5

# run the tests:
pytest

# see the container logs, then remove the containers
docker logs testshipper
docker rm -f testdb testshipper
```

### Online integration tests

The steps of the manual tests also provide the structure for automated tests, see `.travis.yml`.
