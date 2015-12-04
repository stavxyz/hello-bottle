#!/usr/bin/env python

from __future__ import print_function

from gevent import monkey  # noqa
monkey.patch_all()  # noqa

import json
import logging
import operator
import sys
import traceback

import bottle
import bson
import pymongo


# __about__
__title__ = 'hello-bottle'
__summary__ = 'It says hello.'
__url__ = 'https://github.com/samstav/hello-bottle'
__version__ = '1.0.0'
__author__ = 'Rackers'
__email__ = 'smlstvnh@gmail.com'
__keywords__ = ['python', 'bottle', 'docker', 'rancher']
__license__ = 'Apache License, Version 2.0'
# __about__


LOG = logging.getLogger(__name__)

#
# Monkey patch json for bson.ObjectId
#

def _default(self, obj):
    """ObjectId patch for json."""
    if isinstance(obj, bson.ObjectId):
        return str(obj)
    return _default.default(obj)


_original, json.JSONEncoder.default = json.JSONEncoder.default, _default
_default.default = _original


#
# Bottle app & routes
#

bottle_app = application = app = bottle.Bottle()


def httperror_handler(error):
    """Format error responses properly, return the response body.

    This function can be attached to the Bottle instance as the
    default_error_handler function. It is also used by the
    FormatExceptionMiddleware.
    """
    status_code = error.status_code or 500
    output = {
        'code': status_code,
        'message': error.body or 'Oops.',
        'reason': bottle.HTTP_CODES.get(status_code) or None,
    }
    if bottle.DEBUG:
        LOG.warning("Debug-mode server is returning traceback and error "
                    "details in the response with a %s status.",
                    error.status_code)
        if error.exception:
            output['exception'] = repr(error.exception)
        else:
            if any(sys.exc_info()):
                output['exception'] = repr(sys.exc_info()[1])
            else:
                output['exception'] = None

        if error.traceback:
            output['traceback'] = error.traceback
        else:
            if any(sys.exc_info()):
                # Otherwise, format_exc() returns "None\n"
                # which is pretty silly.
                output['traceback'] = traceback.format_exc()
            else:
                output['traceback'] = None
    error.set_header('Content-Type', 'application/json')
    error.body = [json.dumps(output)]
    return error.body


@bottle_app.get('/')
def hello():
    return "Hello World!\n"


@bottle_app.get('/version')
def hello():
    return {
        'version': __version__,
    }


@bottle_app.get('/docs/<object_id>')
def get_document(object_id):
    mc = _mongoclient()
    found = mc.find_one({"_id": bson.ObjectId(object_id)})
    if not found:
        bottle.abort(404, "Document '%s' not found" % object_id)
    return found


@bottle_app.post('/docs')
def set_document():
    mc = _mongoclient()
    inserted = mc.insert_one(bottle.request.json.copy())
    if inserted.acknowledged:
        bottle.response.status = 201
    return {'id': inserted.inserted_id}


#
# Mongo
#

def _mongoclient(*args, **kwargs):
    """Return 'hellobottle' database 'docs' Collection object."""
    if not hasattr(_mongoclient, 'client'):
        _mongoclient.client = pymongo.MongoClient(*args, **kwargs)
    # Returns the 'hellobottle' database, 'docs' collection interface.
    return _mongoclient.client.hellobottle.docs


#
# Utils
#

def fmt_pairs(obj, indent=4, sort_key=None):
    """Format and sort a list of pairs, usually for printing.

    If sort_key is provided, the value will be passed as the
    'key' keyword argument of the sorted() function when
    sorting the items. This allows for the input such as
    [('A', 3), ('B', 5), ('Z', 1)] to be sorted by the ints
    but formatted like so:

        l = [('A', 3), ('B', 5), ('Z', 1)]
        print(fmt_pairs(l, sort_key=lambda x: x[1]))
            Z 1
            A 3
            B 5

        where the default behavior would be:
        print(fmt_pairs(l))
            A 3
            B 5
            Z 1
    """
    longest = max([len(x[0]) for x in obj])
    obj = sorted(obj, key=sort_key)
    formatter = '%s{: <%d} {}' % (' '*indent, longest)
    string = '\n'.join([formatter.format(k, v) for k, v in obj])
    return string


def fmt_routes(bapp):
    """Return a pretty formatted string of the list of routes."""
    routes = [(r.method, r.rule) for r in bapp.routes]
    string = 'Routes:\n'
    string += fmt_pairs(routes, sort_key=operator.itemgetter(1))
    return string


#
#  Run
#


def main(bottle_args, mongo_args):
    mc = _mongoclient(**mongo_args)
    if bottle_args.get('debug'):
        bottle.debug(True)

    bottle_app.default_error_handler = httperror_handler
    print('\n{}'.format(fmt_routes(bottle_app)), end='\n\n')
    bottle.run(bottle_app, **bottle_args)


def _setup_log_options(parser):
    # Logging options
    default = logging.INFO
    loglevel_group = parser.add_argument_group(
        title='Logging options').add_mutually_exclusive_group()
    loglevel_group.add_argument(
        '--verbose', '-v',
        help='Run with a DEBUG loglevel to stdout',
        action='store_const', const=logging.DEBUG,
        dest='loglevel',
        default=default,
    )
    loglevel_group.add_argument(
        '--silent',
        help='Run *without* logging to stdout',
        dest='loglevel',
        const=False, action='store_const',
        default=default,
    )
    loglevel_group.add_argument(
        '--log-level', '-l',
        help=('Run with this loglevel (e.g. debug, warning, '
              'info, etc.) on the logging handler'),
        type=lambda x: getattr(logging, x.upper(), None) or int(x),
        default=default,
        dest='loglevel',
    )



def cli():

    import argparse
    import atexit
    import sys

    parser = argparse.ArgumentParser(
        description="Hello Bottle Application.",
    )
    _setup_log_options(parser)

    parser.add_argument(
        '--server', '-s',
        help='Server adapter to use. See bottle.server_names',
        default='gevent',
    )
    parser.add_argument(
        '--host', '-t',
        help='Server address to bind to.',
        default='0.0.0.0',
    )
    parser.add_argument(
        '--port', '-p',
        default=8080,
        help='Server port to bind to.',
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help=('Run bottle server with debug=True which is useful for '
              'development or troubleshooting. Warning: This may expose raw '
              'tracebacks and unmodified error messages in responses! Note: '
              'this is not an option to configure DEBUG level logging.'),
        default=True,
    )

    #
    # MONGO
    #
    parser.add_argument(
        '--mongo-host',
        help='MongoDB Server address to bind to.',
        default='127.0.0.1',
    )
    parser.add_argument(
        '--mongo-port',
        type=int,
        default=27017,
        help='MongoDB Server port to bind to.',
    )

    # Parse args and run the program.
    args = parser.parse_args()

    if args.loglevel is False:
        logging.getLogger().addHandler(logging.NullHandler())
    else:
        logging.basicConfig(
            level=args.loglevel,
            stream=sys.stderr,
            format='%(message)s'
        )
    # unpack args
    bottle_args = {
        'server': args.server,
        'host': args.host,
        'port': args.port,
        'debug': args.debug,
    }

    mongo_args = {
        'host': args.mongo_host,
        'port': args.mongo_port,
    }
    main(bottle_args, mongo_args)


if __name__ == '__main__':
    cli()
