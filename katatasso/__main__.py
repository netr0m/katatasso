#!/usr/bin/env python
# -*- coding: utf-8 -*-
import getopt
import os
import sys

import katatasso
from katatasso.helpers.logger import increase_log_level, log_to_file
from katatasso.helpers.logger import rootLogger as logger
from katatasso.helpers.const import CATEGORIES

current = os.path.realpath(os.path.dirname(__file__))
APPNAME = 'katatasso'


INDENT = '  '
HELPMSG = f'''usage: {APPNAME} (-f <INPUT_FILE> | -s) [-n] [-a <ALGO>] [-l <NUM_SAMPLES>] [-t <VERSION>] [-c <VERSION>] [-d <FORMAT>] [-o <OUTPUT_FILE>] [-v] [-l]
    Input:
    {INDENT * 1}-f, --infile        {INDENT * 2}Extract entities from file.
    {INDENT * 1}-s, --stdin         {INDENT * 2}Extract entities from STDIN.

    Options:
    {INDENT * 1}-n, --std           {INDENT * 2}Standardize the data. Used with `--train`.
    {INDENT * 1}-a, --algo          {INDENT * 2}Specify the algorithm to use.
                              Can be either `cnb` (Complement NB) or `mnb` (Multinomial NB)
    {INDENT * 1}-l, --limit         {INDENT * 2}Use n samples from each category.

    Action:
    {INDENT * 1}-t, --train         {INDENT * 2}Train and create a model for classification. Specify either `v1` or `v2` as arg.
    {INDENT * 1}-c, --classify      {INDENT * 2}Classify the text. Specify either `v1` or `v2` as arg,
                              depending on what mode was used for training.

    Output:
    {INDENT * 1}-o, --outfile       {INDENT * 2}Output results to this file.
    {INDENT * 1}-d, --format        {INDENT * 2}Output results as this format.
                              Available formats: [plain (default), json]

    General options:
    {INDENT * 1}-v, --verbose       {INDENT * 2}Increase verbosity (can be used several times, e.g. -vvv).
    {INDENT * 1}-l, --log-file      {INDENT * 2}Write log events to the file `{APPNAME}.log`.
    {INDENT * 1}--help              {INDENT * 2}Print this message.
'''


def main():
    TEXT = None
    CONFIG = {}

    result = {}

    if len(sys.argv) < 2:
        print(HELPMSG)
        logger.critical('No input specified')
        sys.exit(2)
    
    argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(argv, 'hf:st:c:na:l:o:d:v', ['help', 'infile=', 'stdin', 'std', 'algo=', '--limit', 'train=', 'classify=', 'outfile=', 'format=', 'verbose', 'log-file'])
    except getopt.GetoptError:
        print(HELPMSG)
        sys.exit(2)

    if not opts:
        print(HELPMSG)
        sys.exit(0)

    """
    Increase verbosity
    """
    opts_v = len(list(filter(lambda opt: opt == ('-v', ''), opts)))
    if opts_v > 4:
        opts_v = 4
    v = 0
    while v < opts_v:
        increase_log_level()
        v += 1
    
    """
    Log to file
    """
    if v > 0:
        enable_logfile = list(filter(lambda opt: opt[0] in ('--log-file'), opts))
        if enable_logfile:
            log_to_file()
    
    for opt, arg in opts:
        if opt == '--help':
            print(HELPMSG)
            sys.exit(0)
        elif opt in ('-f', '--infile'):
            file_path = arg
            logger.debug(f'Using input file {file_path}')
            try:
                with open(file_path, 'r') as f:
                    TEXT = f.read()
            except FileNotFoundError:
                logger.critical(f'The specified file {file_path} does not exist.')
                sys.exit(2)
            except Exception as e:
                logger.critical(f'An error occurred while reading the file `{file_path}`.')
                logger.error(e)
                sys.exit(2)
        elif opt in ('-s', '--stdin'):
            try:
                logger.debug(f'Using input from STDIN')
                TEXT = sys.stdin.read()
            except Exception as e:
                logger.critical(f'An error occurred while reading from stdin.')
                logger.error(e)
                sys.exit(2)
        elif opt in ('-n', '--std'):
            logger.debug(f'OPTION: Standardizing data.')
            CONFIG['std'] = True
        elif opt in ('-a', '--algo'):
            logger.debug('OPTION: Using Complement Naïve Bayes algorithm')
            if arg not in ['mnb', 'cnb']:
                print(HELPMSG)
                logger.critical(f'The specified algorithm `{arg}` is not available.')
                sys.exit(2)
            else:
                CONFIG['algo'] = arg
        elif opt in ('-l', '--limit'):
            if arg.isnumeric:
                logger.debug(f'OPTION: Using n={arg} samples.')
                CONFIG['n'] = int(arg)
            else:
                print(HELPMSG)
                logger.critical(f'n={arg} is non-numeric.')
                sys.exit(2)
        elif opt in ('-t', '--train'):
            logger.debug(f'ACTION: Creating model from dataset')
            if arg == 'v1':
                katatasso.train(
                    std=CONFIG.get('std', False),
                    algo=CONFIG.get('algo', 'mnb')
                )
            elif arg == 'v2':
                katatasso.trainv2(
                    std=CONFIG.get('std', False),
                    algo=CONFIG.get('algo', 'mnb'),
                    n=CONFIG.get('n', None)
                )
            else:
                logger.critical(f'Please specify either `v1` or `v2`. E.g. `katatasso -t v2`')
                sys.exit(2)
        elif opt in ('-c', '--classify'):
            if TEXT:
                logger.debug(f'ACTION: Classifying input')
                if CONFIG.get('cnb'):
                    algo = 'cnb'
                else:
                    algo = 'mnb'
                if arg == 'v1':
                    category = katatasso.classify(TEXT, algo=algo)
                elif arg == 'v2':
                    category = katatasso.classifyv2(TEXT, algo=algo)
                else:
                    logger.critical(f'Please specify either `v1` or `v2`. E.g. `katatasso -c v2`')
                    sys.exit(2)
                result = { 'category': category, 'accuracy': 'n/a', 'alias': CATEGORIES.get(category) }
            else:
                logger.critical(f'Missing input (specify using -f or -s)')
                sys.exit(2)
        elif opt in ('-o', '--outfile'):
            logger.debug(f'CONFIG: Setting output file to {arg}')
            CONFIG['outfile'] = arg
        elif opt in ('-d', '--format'):
            if arg in ['plain', 'json']:
                logger.debug(f'CONFIG: Setting output file format to {arg}')
                CONFIG['format'] = arg
            else:
                logger.critical('Invalid format. Must be one of [plain, json]')
                sys.exit(2)
        
    if result:
        outformat = CONFIG.get('format')
        outfile = CONFIG.get('outfile')
        if outfile:
            ext = 'json' if outformat == 'json' else 'txt'
            fname = f'{outfile}.{ext}'
            if outformat == 'plain':
                with open(fname, 'w') as f:
                    f.write('\n'.join(list(result.values())))
            elif outformat == 'json':
                import json
                with open(fname, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
            logger.debug(f'Results saved to file `{fname}`')
            sys.exit(0)
        else:
            for k,v in result.items():
                print(f'{k}: {v}')
            sys.exit(0)


if __name__ == '__main__':
    main()
