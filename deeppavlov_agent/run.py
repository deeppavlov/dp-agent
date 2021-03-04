import argparse

from .cmd_client import run_cmd
from .run_http import run_http
from .run_tg import run_telegram


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pl', '--pipeline_configs', help='Pipeline config (overwrite value, defined in settings)',
                        type=str, action='append')
    parser.add_argument("-ch", "--channel", help="run agent in telegram, cmd_client or http_client", type=str,
                        choices=['cmd_client', 'http_client', 'telegram'], default='cmd_client')
    parser.add_argument('-p', '--port', help='port for http client, default 4242', default=4242)
    parser.add_argument('-c', '--cors', help='whether to add CORS middleware to http_client',
                        action='store_true', default=None)
    parser.add_argument('-d', '--debug', help='run in debug mode', action='store_true')
    parser.add_argument('-tl', '--time_limit', help='response time limit, 0 = no limit', type=int, default=0)
    parser.add_argument('-ul', '--uib_login', help='The Unified Inbox access login', type=str, default=None)
    parser.add_argument('-up', '--uib_password', help='The Unified Inbox access password', type=str, default=None)
    args = parser.parse_args()

    if args.channel == 'cmd_client':
        run_cmd(args.pipeline_configs, args.debug)
    elif args.channel == 'http_client':
        run_http(args.port, args.pipeline_configs, args.debug, args.time_limit, args.cors, args.uib_login,
                 args.uib_password)
    elif args.channel == 'telegram':
        run_telegram(args.pipeline_configs)


if __name__ == '__main__':
    main()
