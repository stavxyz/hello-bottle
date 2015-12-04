#!/usr/bin/env python

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


from bottle import route, run

@route('/')
def hello():
    return "Hello World!\n"


def main():
    run(host='0.0.0.0', port=8080, debug=True)


def cli():
    main()


if __name__ == '__main__':
    cli()
