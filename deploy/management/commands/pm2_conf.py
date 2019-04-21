from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    # 生成PM2配置文件: python manage.py pm2_conf --socket unix://xxxxx/xxxx.sock
    help = 'Generate a PM2 configure file for current socket path'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        # https://docs.python.org/3/library/argparse.html#nargs
        parser.add_argument('--task_prefix', dest='task_prefix', required=True, nargs='?', type=str,
                            help='task prefix')  # 任务名称前缀
        parser.add_argument('--name', dest='version', required=True, nargs='?', type=str,
                            help='version')  # version是系统参数
        parser.add_argument('--app_name', dest='app_name', required=True, nargs='?', type=str,
                            help='app name')
        parser.add_argument('--home', dest='home', required=True, nargs='?', type=str,
                            help='project home path')
        parser.add_argument('--socket_path', dest='socket_path', required=True, nargs='?', type=str,
                            help='socket path')
        parser.add_argument('--venv_path', dest='venv_path', required=True, nargs='?', type=str,
                            help='venv path')
        pass

    def handle(self, *args, **options):
        self.generate_by_template(version=options['version'], socket_path=options['socket_path'],
                                  venv_path=options['venv_path'], app_name=options['app_name'],
                                  home=options['home'], task_prefix=options['task_prefix'])

    @staticmethod
    def generate_by_template(task_prefix, version, venv_path, socket_path, app_name, home):
        template = 'deploy/ecosystem.config.template'
        variables = {
            "task_prefix": task_prefix,
            "version": version,
            "venv_path": venv_path,
            "socket_path": socket_path,
            "app_name": app_name,
            "deploy_path": home
        }
        print(render_to_string(template, variables))
