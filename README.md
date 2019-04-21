# Django Deploy

For deploy Django project on Linux server.

Features:

1. Automatic

2. Zero downtime

3. Multiple version

4. Easy rollback


## Requirements on server

* Nginx
* Anaconda
* Nodejs
* PM2

## Quick start

1. Add "deploy" to your INSTALLED_APPS setting like this:

```python
INSTALLED_APPS = [
    ...
    'deploy',
]
```

2. Configure ssh:

3. 