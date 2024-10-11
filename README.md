## Introduction

The project works on a dataset of trajectories, derived from a modified version of the Geolife GPS Trajectory dataset. Additionally, it contained code snippets for database connectivity using Python and examples of various MySQL queries. The primary objectives were to preprocess the dataset, design appropriate tables in a MySQL database, populate these tables with the cleaned data, and perform a series of queries via Python to extract meaningful insights from the database. The dataset is available here: [Geolife Trajectories 1.3](https://download.microsoft.com/download/F/4/8/F4894AA5-FDBC-481E-9285-D5F8C4C4F039/Geolife%20Trajectories%201.3.zip)

The repository can be found at [plebbimon/tdt4225](https://github.com/plebbimon/tdt4225).

## Setup

This project relies on poetry for dependency management. Once poetry is installed, we can proceed with installing the project dependencies. To install the required dependencies, run the following command:

```bash
poetry install
```

One can also enter the shell the same way as you would with any other venv:

```bash
poetry shell
```

## Usage

To insert data into the database, run the following command:

```bash
poetry run python insertion_script.py
```

To run the queries, run the following command:

```bash
poetry run python queries.py
```