# Family Link

[![PyPI version](https://badge.fury.io/py/familylink.svg)](https://badge.fury.io/py/familylink)

A non-official Python package to interact with Google Family Link, to manage your kids' screen time.

<p align="center">
  <img src="logo.svg" alt="Family Link logo" width="200" height="200">
</p>

## Installation

```bash
pip install familylink
```

## Usage as a CLI

Create a `config.csv` file with the following format:

```csv
App,Max Duration,Days,Time Ranges
Calculator,,,                       # always allowed
Youtube,0:10,Mon-Fri,               # 10 minutes per day during weekdays
Youtube,0:30,Sat-Sun,               # 30 minutes per day on weekends
Fortnite,1:00,Wed,13:00-18:00       # 1 hour on Wednesday, between 13:00 and 18:00
Fortnite,1:00,Sat-Sun,09:30-18:00   # 1 hour on weekends, between 09:30 and 18:00
Google Photos,0:10,,                # 10 minutes everyday
```

The apps that are not in the list will be blocked.

```bash
python -m familylink.cli config.csv --dry-run  # Remove --dry-run to apply changes
# or with uv
uvx familylink config.csv --dry-run
```

## Usage as a library

### Create a client

```python
from familylink import FamilyLink

client = FamilyLink()
```

### Set an app limit

```python
client.set_app_limit("Spotify", 30)  # in minutes
```

### Block an app

```python
client.block_app("Youtube")
```

### Always allow an app

```python
client.always_allow_app("Calculator")
```

### Remove an app limit

```python
client.remove_app_limit("Youtube")
```

### List apps and usage

```python
client.print_usage()
# ------------------------------
# Limited apps
# ------------------------------
# Spotify: Music and Podcasts: 30 minutes
# 
# ------------------------------
# Blocked apps
# ------------------------------
# YouTube
# 
# ------------------------------
# Always allowed apps
# ------------------------------
# Calculator
# 
# ------------------------------
# Usage per app (today)
# ------------------------------
# Spotify: Music and Podcasts: 00:30:09
```
