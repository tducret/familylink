# Family Link

A Python package to interact with Google Family Link.

## Installation

```bash
pip install familylink
```

## Usage

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
