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

* install

```bash
pip install django-deploy-kit
```

* use

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
    module.exports = {
        apps : [
            {
            name   : '{{ task_prefix }}{{ version }}',
            script : '{{ venv_path }}/bin/gunicorn',
            interpreter: '{{ venv_path }}/bin/python',
            args : [
                    '--workers', '3',
                    '--timeout', '600',
                    '--bind', '{{ socket_path }}',
                    '{{ app_name }}.wsgi:application'
            ],
            cwd : '{{ deploy_path }}',
            env: {
                PYTHONPATH: '{{ deploy_path }}/{{ app_name }}',
                PATH: '{{ deploy_path }}:{{ venv_path }}/bin/:{{ deploy_path }}/{{ app_name }}/'
            },
            "exec_mode": "fork"
            }
        ]
    };
    ```
    
    content of `nginx.conf.template`

    ```bash
    upstream {{ app_name }}-website {
        server 127.0.0.1;
    }

    server {
        listen 80;
        client_max_body_size 1G;
        gzip on;

        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        location /static {
            alias {{ static_path }};
            mp4;
            mp4_buffer_size       1m;
            mp4_max_buffer_size   5m;
        }

        location / {
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_pass  http://{{ unix_socket }};

            proxy_redirect     off;
            proxy_set_header   Host             $host;
            proxy_set_header   X-Real-IP        $remote_addr;
            proxy_set_header   X-Forwarded-For  $remote_addr;
            proxy_set_header   X-Forwarded-Host $remote_addr;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
            proxy_buffering            off;
            proxy_max_temp_file_size   0;
            proxy_connect_timeout      600s;
            proxy_send_timeout         600s;
            proxy_read_timeout         600s;
            proxy_buffer_size          4k;
            proxy_buffers              4 32k;
            proxy_busy_buffers_size    64k;
            proxy_temp_file_write_size 64k;
        }

        error_page 404 /404.html;

        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
    ```
