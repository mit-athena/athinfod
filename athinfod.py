#!/usr/bin/python
import fnmatch
import os
import socket
import string
import sys

BASE_DEFINITIONS = '/etc/athena/athinfo.defs'
EXTENDED_DEFINITIONS = '/etc/athena/athinfo.defs.d/'

def read_query():
    line = sys.stdin.readline().strip()
    if any(x not in string.printable for x in line):
        raise Exception('invalid query')
    return line

def shutdown_input():
    std_in = sys.stdin.fileno()
    sys.stdin.close()
    fd = os.open("/dev/null", os.O_RDONLY)

    if fd != std_in:
        os.dup2(fd, std_in)
        os.close(fd)

def get_definitions_from_file(queries, filepath):
    with open(filepath, "r") as defs:
        for line in defs:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            (query, shell_command) = string.split(line, maxsplit=1)
            queries[query] = [shell_command, False]
    return queries

def get_query_access(filepath, queries):
    enablement = {'enable': True, 'disable': False}
    with open(filepath, "r") as access:
        for line in access:
            (action, query) = string.split(line.strip(), maxsplit=1)
            if action not in enablement:
                raise Exception('Invalid syntax in athinfo.access')
            if query not in queries and query != '*':
                raise Exception(
                    'athinfo.access references query "%s" that is not defined' %
                    (query,))
            for (key, value) in queries.iteritems():
                if key == query or query == '*':
                    queries[key][1] = enablement[action]

def get_definition(query):
    queries = {}
    get_definitions_from_file(queries, BASE_DEFINITIONS)
    for candidate in os.listdir(EXTENDED_DEFINITIONS):
        if fnmatch.fnmatch(candidate, '*.defs'):
            get_definitions_from_file(queries, os.path.join(
                    EXTENDED_DEFINITIONS, candidate))
    get_query_access("/etc/athena/athinfo.access", queries)
    if query not in queries:
        raise Exception('unknown query "%s"' % (query,))
    cmd, enabled = queries[query]
    if not enabled:
        raise Exception('query "%s" is disabled' % (query,))
    return cmd

def main():
    query = read_query()
    shutdown_input()
    cmd = get_definition(query)
    os.execv("/bin/sh", ['sh', '-c', cmd])

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print >>sys.stderr, "athinfod: %s" % (e,)
        sys.exit(1)
