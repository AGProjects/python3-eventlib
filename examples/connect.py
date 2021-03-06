# Copyright (c) 2008-2009 AG Projects
# Author: Denis Bilenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Spawn multiple workers and collect their results.

Demonstrates how to use eventlib.green package and proc module.
"""
from eventlib import proc
from eventlib.green import socket

# this example works with both standard eventlib hubs and with twisted-based hub
# uncomment the following line to use twisted hub
#from twisted.internet import reactor

def geturl(url):
    sock = socket
    c = sock.socket()
    ip = socket.gethostbyname(url)
    #conn = c.connect((ip, 80))
    #print('%s connected %s' % (url, ip))
    #sent = c.send('GET /\r\n\r\n')
    return "#" #c.recv(1024)

urls = ['www.google.com', 'www.python.org', 'www.yandex.ru'] #, 'ag-projects.com'] #, 'sylkserver.com']
jobs = [proc.spawn(geturl, x) for x in urls]
print('spawned %s jobs' % len(jobs))

# collect the results from workers
print("WAITALL", jobs)
results = proc.waitall(jobs)
# Note, that any exception in the workers will be reraised by waitall
# unless trap_errors argument specifies otherwise

for url, result in zip(urls, results):
    print('%s: %s' % (url, repr(result)[:50]))

