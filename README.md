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

    add host config in `~/.ssh/config`
    
    ```bash
    Host host1
        Hostname xxx.xxx.xxx.xxx
        Port 2222
        User xxxx
        ServerAliveInterval 60
        # IdentityFile ~/.ssh/id_rsa_xxxxx
    ```
    
    create ssh-key file
    
    ```bash
    ssh-keygen -t rsa -C "xxxx@xxxx.com"
    ```
    
    you could leave a blank for password, when you execute ssh command it will not ask your password again

3. Add definition in settings of Django app

    ```python
    GIT_URL = 'git@github.com:path/name.git'
    GIT_DEPLOY_BRANCH = 'stable'
    APP_NAME = 'appname'

    DEPLOY = {
        "host1": {  # same as ssh-config
            "task_prefix": "app-process",  # prefix of process name
            "home_path": '/path/to/appname/www',  # path of each versions
            "static_path": '/path/to/appname/statics',  # path of statics for each versions
            "conda_path": '/path/to/anaconda3/bin',  # path of anaconda bin 
            "nginx_conf": "/etc/nginx/sites-enabled/appname",  # enabled site config of Nginx
            "fixed_deploy_path": '/path/to/appname/fixed', # use to do migrate
        }
    }
    ```

4. create PM2 and Nginx configure template

    create directory name of `deploy` in your base path of Django app 
    
    ```bash
    deploy/
    └── templates
        └── deploy
            ├── ecosystem.config.template
            └── nginx.conf.template
    ```
    
    content of `ecosystem.config.template`
    
    ```bash
    ...
    ```
    
    content of `nginx.conf.template`
