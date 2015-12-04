import logging
import multiprocessing
import os
import pprint
import random
import socket
import string
import subprocess
import sys
import threading
import unittest

try:
    import queue
except ImportError:
    import Queue as queue

import mongobox
import requests

import hello


LOG = logging.getLogger(__name__)


def get_free_port(host):
    sock = socket.socket()
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    del sock
    return port


def _queued_output(out):
    """Use a separate process to read server stdout into a queue.
    Returns the queue object. Use get() or get_nowait() to read
    from it.
    """
    def _enqueue_output(_out, _queue):
        for line in _out:
            _queue.put(line)
    output_queue = multiprocessing.Queue()
    # I tried a Thread, it was blocking the main thread because
    # of GIL I guess. This made me very confused.
    process = multiprocessing.Process(
        target=_enqueue_output, args=(out, output_queue))
    process.daemon = True
    process.start()
    return output_queue


class TestServerFunctional(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.host = '127.0.0.1'
        cls.port = get_free_port(cls.host)
        cls.url = 'http://%s:%s' % (cls.host, cls.port)
        cls.test_env = ''.join(random.sample(string.hexdigits, 22))
        # Using hello.__path__ instead of just `hello-bottle`
        # to ensure we don't get a rogue binary.
        # Use sys.executable to ensure we run the server using
        # the exact same python interpreter as this test is using.
        cls._mbox = mongobox.MongoBox()
        cls._mbox.start()
        cls.mongoclient = cls._mbox.client() # pymongo client 
        assert cls._mbox.running()

        exe = os.path.realpath(hello.__file__)
        assert os.path.isfile(exe)
        argv = [
            sys.executable,
            exe,
            '--host', cls.host,
            '--port', str(cls.port),
            '--verbose',
            '--debug',
            '--server', 'gevent',
            '--mongo-port', str(cls._mbox.port),
        ]

        server_started = "Listening on {url}/".format(url=cls.url)

        # ensure a hard-coded os.environ when testing!
        # Without the unbuffered flag this doesn't
        # work in > Python 3.
        _env = {
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONUNBUFFERED': '1',
        }
        # bufsize=1 means line buffered.
        # universal_newlines=True makes stdout text and not bytes
        cls.server = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=_env,
        )

        cls._timeout = 5
        startup_timeout = threading.Timer(cls._timeout, cls.server.kill)
        startup_timeout.daemon = True
        startup_timeout.start()

        cls.non_blocking_read_queue = _queued_output(cls.server.stdout)
        # cls.server.poll() will return -9 if Timer kill() sends SIGKILL
        while cls.server.poll() is None:
            try:
                line = cls.non_blocking_read_queue.get_nowait()
            except queue.Empty:
                continue
            else:
                LOG.debug("Test hello-bottle server STDOUT: %s", line)
                if server_started in line:
                    startup_timeout.cancel()
                    LOG.info("hello-bottle server started successfully!")
                    break

    def setUp(self):
        """Ensure that the server started."""
        code = self.server.poll()
        # if code is None: server running.
        # if code is 0, server exited for some reason.
        if code:
            if code == -9:
                self.fail("Failed to start hello-bottle server within "
                          "the %s second timeout!" % self._timeout)
            else:
                self.fail("Failed to start test hello-bottle process! "
                          "Exit code: %s" % code)
        if code == 0:
            self.fail("Server died for some reason with a 0 exit code.")

        self.session = requests.session()
        # Set up retries to not fail during server startup delay
        retry = requests.packages.urllib3.util.Retry(
            total=5, backoff_factor=0.2)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self.session.mount(self.url, adapter)

    @classmethod
    def tearDownClass(cls):
        cls._mbox.stop()
        assert not cls._mbox.running()
        while not cls.non_blocking_read_queue.empty():
            line = cls.non_blocking_read_queue.get_nowait()
            LOG.debug("POST-MORTEM test hello-bottle server STDOUT: %s", line)
        try:
            cls.server.kill()
        except OSError:
            pass

    def _check_response(self, response):
        """Check for 500s and debug-tracebacks."""
        if response.status_code == 500:
            req = response.request
            try:
                body = response.json()
                if 'traceback' in body:
                    msg = ('Traceback from test hello-bottle server '
                           'when calling {m} {p}\n{tb}')
                    self.fail(
                        msg.format(m=req.method,
                                   p=req.path_url,
                                   tb=body['traceback'])  # fail
                    )
                else:
                    self.fail(pprint.pformat(body, indent=2))
            except (TypeError, ValueError):
                pass

    def test_version(self):
        vers = self.session.get('{}/version'.format(self.url))
        self._check_response(vers)
        vers = vers.json()
        expected = {
            'version': hello.__version__
        }
        self.assertEqual(expected, vers)

    def test_not_found(self):
        response = self.session.get('{}/i/dont/exist'.format(self.url))
        self._check_response(response)
        self.assertEqual(404, response.status_code)

    def test_post_and_get_document(self):

        data = {'junk': ''.join(random.sample(string.hexdigits, 22))}
        create = self.session.post(
            '{}/docs'.format(self.url), json=data)
        object_id = create.json()['id']
        response = self.session.get(
            '{}/docs/{}'.format(self.url, object_id))
        expected = data.copy()
        expected['_id'] = object_id
        self.assertEqual(response.json(), expected)


if __name__ == '__main__':
    opts = {}
    if any(v in ' '.join(sys.argv) for v in ['--verbose', '-v']):
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        opts['verbosity'] = 2
    unittest.main(**opts)
