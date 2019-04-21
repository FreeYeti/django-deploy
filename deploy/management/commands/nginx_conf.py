from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    # 生成当前版本Nginx配置文件:
    # python manage.py nginx_conf --app_name forest --socket unix://xxxxx/xxxx.sock --static xxxxx/xxxx/xxx
    help = 'Generate a Nginx configure file for current socket path'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        # https://docs.python.org/3/library/argparse.html#nargs
        parser.add_argument('--app_name', dest='app_name', required=True, nargs='?', type=str, help='name of app')
        parser.add_argument('--socket', dest='socket', required=True, nargs='?', type=str, help='socket path')
        parser.add_argument('--static', dest='static', required=True, nargs='?', type=str, help='statics path')
        pass

    def handle(self, *args, **options):
        self.generate_by_template(app=options['app_name'], socket=options['socket'], static=options['static'])

    @staticmethod
    def generate_by_template(app, socket, static):
        template = 'deploy/nginx.conf.template'
        variables = {
            "app_name": app,
            "unix_socket": socket,
            "static_path": static
        }
        print(render_to_string(template, variables))
