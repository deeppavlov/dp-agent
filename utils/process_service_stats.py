"""Module to process Agent services logs.

By default this module processes logs from last modified file from directory `logs` (except `stats.log`) and writes
results to `logs/stats.log` file.

Example:
    python utils/process_service_stats.py [-m <mode>] [-v <verbose>] [-f <log_file_to_process>]

"""

from argparse import ArgumentParser

from core.log import ResponseLogger, log_dir_path

parser = ArgumentParser()
parser.add_argument('-m', '--mode', help='stat collect mode', default='rps', choices=['rps', 'avg'])
parser.add_argument('-v', '--verbose', help='set services response logging verbosity level', type=str, default='agent',
                    choices=['agent', 'service', 'both'])
parser.add_argument('-f', '--file', help='service log file name', type=str, default=None)


def main() -> None:
    args = parser.parse_args()
    if not args.file:
        log_files = [p for p in log_dir_path.iterdir() if p.name != 'stats.log']
        latest = max(log_files, key=lambda p: p.stat().st_ctime)
        file = latest.name
    else:
        file = args.file
    rl = ResponseLogger(args.verbose, file)
    if args.mode == 'rps':
        rl.get_rps()
    elif args.mode == 'avg':
        rl.get_avg_time()


if __name__ == '__main__':
    main()
