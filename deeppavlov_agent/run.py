"""

This module is now obsolete. Delete it or move hydra decorators here to be able to use it.

"""
import argparse

from .run_cmd import run_cmd
from .run_http import run_http
from .run_tg import run_telegram


CHANNELS = {
    "cmd_client": run_cmd,
    "http_client": run_http,
    "telegram": run_telegram,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-ch",
        "--channel",
        help="run agent in telegram, cmd_client or http_client",
        type=str,
        choices=list(CHANNELS.keys()),
        default="cmd",
    )
    parser.add_argument(
        "-pl",
        "--pipeline_configs",
        help="Pipeline config (overwrite value, defined in settings)",
        type=str,
        action="append",
    )
    parser.add_argument(
        "-p", "--port", help="port for http client, default 4242", default=4242
    )
    parser.add_argument(
        "-c",
        "--cors",
        help="whether to add CORS middleware to http_client",
        action="store_true",
        default=None,
    )
    parser.add_argument("-d", "--debug", help="run in debug mode", action="store_true")
    parser.add_argument(
        "-tl",
        "--time_limit",
        help="response time limit, 0 = no limit",
        type=int,
        default=0,
    )
    args = parser.parse_args()

    run_channel = CHANNELS[args.channel]
    run_channel()

    # if args.channel == "cmd_client":
    #     run_cmd(args.pipeline_configs, args.debug)
    # elif args.channel == "http_client":
    #     run_http(
    #         args.port, args.pipeline_configs, args.debug, args.time_limit, args.cors
    #     )
    # elif args.channel == "telegram":
    #     run_telegram()


if __name__ == "__main__":
    main()
