import os
import re
import datetime
import getpass
from fabric import Connection
from colorama import init, Fore
from django.core.management.base import BaseCommand
from django.conf import settings

init(autoreset=True)


class Command(BaseCommand):
    # Deploy
    # example: python manage.py deploy --host foo --pwd xxxxx
    #          python manage.py deploy --host bar
    #
    # Server side:
    #   * Nginx: web server
    #   * Gunicorn: Python WSGI HTTP Server
    #   * PM2: process manager
    #   intro: use PM2 to start gunicorn process, 
    #          gunicorn create unix socket service for each version.
    #          Nginx proxy http request to the unix socket.
    #
    # Tool: use Fabric to execute shell commands remotely
    # prepare: use datetime create a name for directory of current version
    # 1. Extract git archive on the target server. Without `.git` dir.
    # 2. Use `conda` command create virtual environment. (We are using Anaconda)
    # 3. Running `pip install` in virtual environment
    # 4. Build the frontend and collect the statics
    # 5. Processes management
    # [ ] a. Supervisor (normally)
    # [√] b. PM2 in nodejs
    # [ ] c. systemd
    #    Anyway, start app using gunciorn, and create service through the unix socket
    # 6. Create new nginx config for site
    # 7. Reload the nginx
    # 8. Clear history versions that had expired over 3 days
    help = 'Deploy the project to server'

    def __init__(self, *args, **kwargs):
        self.APP = settings.APP_NAME
        self.version = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

        self.conn = None
        self.HOME = None
        self.CONDA_PATH = None
        self.NGINX_CONF = None
        self.TASK_PREFIX = None
        self.STATIC_PATH = None
        self.FIXED_PATH = None
        self.PWD = None

        self.deploy_path = None
        self.venv_path = None
        self.pip_path = None
        self.conda_bin = None
        self.venv_python = None
        self.ECOSYSTEM_PATH = None
        self.socket_path = None
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        # https://docs.python.org/3/library/argparse.html#nargs
        parser.add_argument('--host', dest='host', required=True, nargs='?', type=str, help='host')  # host to deploy
        parser.add_argument('--pwd', dest='pwd', required=False, nargs='?', type=str, help='pwd')  # sudo password
        parser.add_argument('--skip', dest='skip', required=False, nargs='?', type=str, help='skip setp')

    def init_env(self, host, pwd):
        self.HOME = settings.DEPLOY[host]['home_path']
        self.CONDA_PATH = settings.DEPLOY[host]['conda_path']
        self.NGINX_CONF = settings.DEPLOY[host]['nginx_conf']
        self.TASK_PREFIX = settings.DEPLOY[host]['task_prefix']
        self.STATIC_PATH = settings.DEPLOY[host]['static_path']
        self.FIXED_PATH = settings.DEPLOY[host]['fixed_deploy_path']
        self.PWD = pwd

        self.deploy_path = os.path.join(self.HOME, self.version)
        self.venv_path = os.path.join(self.deploy_path, 'virtualenv')
        self.pip_path = os.path.join(self.venv_path, 'bin', 'pip')
        self.conda_bin = os.path.join(self.CONDA_PATH, 'conda')
        self.venv_python = os.path.join(self.venv_path, 'bin', 'python')
        self.ECOSYSTEM_PATH = os.path.join(self.deploy_path, 'ecosystem.config.js')
        self.socket_path = 'unix:{}/{}/{}.sock'.format(self.deploy_path, self.APP, self.APP)

    def handle(self, *args, **options):
        pwd = options['pwd'] or getpass.getpass()

        self.create_conn(host=options['host'])
        self.init_env(host=options['host'], pwd=pwd)
        print(self.test_pwd())
        print(Fore.GREEN + 'Disk use: {}'.format(self.disk_free()))

        # code
        self.new_version()
        print(Fore.GREEN + 'Git archive extracted: {}'.format(self.deploy_path))

        # backend
        self.backend()
        print(Fore.GREEN + 'Backend ready!')

        # Migrations
        self.migrations()
        print(Fore.GREEN + 'Migrate complated')

        # frontend
        self.frontend()
        print(Fore.GREEN + 'Frontend ready!')

        # service
        self.ecosystem()
        if not options['skip'] or options['skip'] == 'nginx':
            self.nginx()
        print(Fore.GREEN + 'Nginx restart success, version updated to {}!'.format(self.version))

        # clear
        deleted = self.clear()
        print(Fore.GREEN + 'deleted versions: {}'.format(str(deleted)))

        # show processes
        self.conn.run('pm2 list --sort name:desc')

    def create_conn(self, host):
        self.conn = Connection(host, connect_kwargs={
            'auth_timeout': 3000,
            'timeout': 3000,
            'banner_timeout': 120
        })

    def test_pwd(self):
        return self.conn.run('echo {} | sudo -S echo "password correct!"'.format(self.PWD), hide=True).stdout.strip()

    def disk_free(self):
        command = "df -h / | tail -n1 | awk '{print $5}'"
        return self.conn.run(command, hide=True).stdout.strip()

    def new_version(self):
        self.conn.run('mkdir {}'.format(self.deploy_path))
        self.conn.run('mkdir {}'.format(self.venv_path))

        self.conn.run('rm -f {}'.format(os.path.join(self.HOME, 'current')))
        self.conn.run('ln -s {} {}'.format(self.deploy_path, os.path.join(self.HOME, 'current')))

        self.conn.run('cd {} && git archive --format=tar --remote={} {} ./ | tar -x'
                      .format(self.deploy_path, settings.GIT_URL, settings.GIT_DEPLOY_BRANCH))

    def backend(self):
        self.conn.run('{} create -y --prefix {} python=3.6'.format(self.conda_bin, self.venv_path))
        # conda create -y --prefix .... python=3.6

        # 由于下载pip包可能出现中断，可用多种源
        # 清华源：https://pypi.tuna.tsinghua.edu.cn/simple
        # 豆瓣源：http://pypi.douban.com/simple/ 需搭配 --trusted-host pypi.douban.com
        # 墙内可能要用到 -i https://pypi.tuna.tsinghua.edu.cn/simple 参数
        # 如果每次都想更新软件包，使用： --no-cache-dir
        self.conn.run('cd {} && {} install'.format(self.deploy_path, self.pip_path) +
                      ' -r requirements.txt')

    def migrations(self):
        # 进入固定部署的目录，执行迁移命令
        self.conn.run('cd {} && git stash'.format(self.FIXED_PATH))
        self.conn.run('cd {} && git pull'.format(self.FIXED_PATH))
        self.conn.run('cd {} && {} manage.py makemigrations'.format(self.FIXED_PATH, self.venv_python))
        self.conn.run('cd {} && {} manage.py migrate'.format(self.FIXED_PATH, self.venv_python))
        print(self.FIXED_PATH)

    def frontend(self):
        self.conn.run('cd {} && yarn install'.format(self.deploy_path))
        self.conn.run('cd {} && yarn build'.format(self.deploy_path))
        self.conn.run('cd {} && {} manage.py collectstatic --noinput'.format(self.deploy_path, self.venv_python))
        self.conn.run('cp -r {} {}'.format(settings.STATIC_ROOT, os.path.join(self.STATIC_PATH, self.version)))

    def pm2_apps(self):
        result = self.conn.run('pm2 list -m | grep "+---\\|status"', hide=True).stdout.strip()
        if result is None or result == '':
            return None

        lines = result.split()
        if len(lines) < 5:
            return None

        apps = []
        for i in range(int(len(lines) / 5)):
            # name: lines[i * 5 + 1]
            # status: lines[i * 5 + 4]
            apps.append([lines[i * 5 + 1], lines[i * 5 + 4]])

        return apps

    def ecosystem(self):
        # 采用PM2管理Gunicorn进程
        self.conn.run('cd {} && {} manage.py pm2_conf'.format(self.deploy_path, self.venv_python) +
                      ' --task_prefix {} --name {} --socket_path {} --venv_path {} --app_name {} --home {} > {}'.
                      format(self.TASK_PREFIX, self.version, self.socket_path, self.venv_path,
                             self.APP, self.deploy_path, self.ECOSYSTEM_PATH))

        self.conn.run('cd {} && pm2 start -s {}'.format(self.deploy_path, self.ECOSYSTEM_PATH))

        apps = self.pm2_apps()

        for app in apps:
            if app[0] == self.TASK_PREFIX + self.version and app[1] == 'errored':
                raise Exception("Failed to deploy! Please check the PM2 ecosystem configure!")

        self.conn.run('cd {} && pm2 save'.format(self.deploy_path))

    def nginx(self):
        self.conn.run('cd {} && {} manage.py nginx_conf --app_name {} --socket {} --static {} > {}'
                      .format(self.deploy_path, self.venv_python, self.APP, self.socket_path,
                              os.path.join(self.STATIC_PATH, self.version), self.NGINX_CONF))
        self.conn.run('echo {} | sudo -S service nginx reload'.format(self.PWD), hide=True)

    @staticmethod
    def write_config(path, content):
        print(path)
        if not os.path.isfile(path):
            os.mknod(path)
        fp = open(path, 'w')
        fp.write(content)
        fp.close()

    def versions(self):
        result = self.conn.run('cd {} && ls'.format(self.HOME), hide=True).stdout.strip()
        files = result.split()
        return files

    def clear(self):
        # 读取部署文件夹，删除3天前的版本，3天内保留5个版本
        # 清理PM2中出错的版本
        files = self.versions()
        files_count = len(files)
        if files_count < 7:
            pass

        deleted = 0

        for file in files:
            try:
                days = (datetime.datetime.now() - datetime.datetime.strptime(file, "%Y%m%d-%H%M%S")).days
                if days > 3 and (files_count - deleted) > 6:
                    self.conn.run('pm2 delete {}'.format(self.TASK_PREFIX + file), hide=True, warn=True)
                    self.conn.run('rm -rf {}'.format(os.path.join(self.HOME, file)))
                    self.conn.run('rm -rf {}'.format(os.path.join(self.STATIC_PATH, file)))
                    deleted += 1
            except ValueError:
                continue

        apps = self.pm2_apps()
        for app in apps:
            if app[1] == 'errored':
                try:
                    app.index(self.TASK_PREFIX)
                    deleted += 1
                    self.conn.run('pm2 delete {}'.format(app[0]), hide=True, warn=True)
                    self.conn.run('rm -rf {}'.format(os.path.join(self.HOME, app[0])))
                except ValueError:
                    continue
            # m = re.match(r'{}(\d+)-(\d+)'.format(self.TASK_PREFIX), app[0])
            # '{}-{}'.format(m.group(1), m.group(2)

        return deleted
