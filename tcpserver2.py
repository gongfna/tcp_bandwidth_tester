#!/usr/bin/env python

'''A TCP server for receiving data from client.'''

from pylab import *
from numpy import *

import select
import socket
#import sys
import threading
#import os
#import pickle
#import time
#import datetime

#Dictionaries are thread safe. Threads might access old values depending on execution order,
#but corrupt values will not result. Also, in this case, each thread will only ever read from,
#or write to, a single thread.
global amount
global client_types

def isOpen(ip,port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      s.connect((ip, port))
      s.shutdown(2)
    except:
      print 'port '+str(port)+' blocked'

class Server:
  def __init__(self, port):
    self.host = ''
    self.port = port 
    self.backlog = 5
    self.size = 1024
    self.socket = None
    self.threads = []

  def open_socket(self):
    try:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a = self.socket.bind((self.host, self.port))
        b = self.socket.listen(self.backlog)
    except socket.error, (value, message):
        if self.socket:
            self.socket.close()
        print "Could not open socket: " + message
        sys.exit(1)

  def run(self):
    self.open_socket()
    input = [self.socket, sys.stdin]
    running = 1

    while running:
        inputready, outputready, exceptready = select.select(input, [], [])

        for s in inputready:

            if s == self.socket:
                c = Client(self.socket.accept())
                c.setDaemon(True) #TODO true or false?
                c.start()
                self.threads.append(c)

            elif s == sys.stdin:
                # handle standard input
                line = sys.stdin.readline()
                if line.strip() == 'q':
                  running = 0
                else:
                  print "Type 'q' to stop the server"

    print 'Received signal to stop'

    self.socket.close()

    for c in self.threads:
        c.running = 0
        c.join()

class BandwidthMonitor(threading.Thread):
  def __init__(self, congestion):
    #key, is the specific congestion control algorithm this bandwidth monitor is associated with. 
    self.start = 0
    self.end = 0
    self.amount_now = 0
    self.key = congestion
    print 'Bandwidth monitor created for TCP ' + self.key

  def initiate(self):
    self.start = time.time()

  def terminate(self):
    self.amount_now = amount[self.key]
    amount[self.key] = 0
    self.end = time.time()

  def get_bandwidth(self):
    return self.amount_now/(self.end - self.start)

class Graph(threading.Thread):
  def __init__(self, congestion):
      threading.Thread.__init__(self) 
      self.key = congestion
      self.running = 1
  
  def run(self):
      print 'Graphing Thread: creating bandwidth monitor and graph for TCP ' + self.key
      b = BandwidthMonitor(self.key)    

      x = arange(0,100,1)
      y = []
   
      ion() #animated graphing

      while len(y) < 100:
          y.append(0)

      current_speed = 140
      line, = plot(x,y,'g')
      axis(array([0, 100, 0, current_speed]))

      xticks([])
      grid('on')
      title('TCP ' + self.key)
      ylabel('Throughput (MB)')
      xlabel('Time (s)')

      axis(array([0, 100, 0, 200]))

      while self.running:
          b.initiate()
          time.sleep(1)
          b.terminate()
          speed = b.get_bandwidth()/(1000*1000) 

          if speed > current_speed:
              current_speed = speed + 40
	      axis(array([0, 100, 0, current_speed]))

          y.pop(0)
          y.append(speed)
          line.set_ydata(y)
          draw()

class Client(threading.Thread): #client thread
  def __init__(self, (client, address)):
    #key is the specific congestion control algorithm this client is associated with.
    threading.Thread.__init__(self) 
    self.client = client #the socket
    self.address = address #the address
    self.size = 1024 #the message size
    self.username = None
    self.running = 1 #running state variable
    self.key = ''

  def run(self):

    #wait for client to indicate its type of congestion control
    data = self.client.recv(self.size)
    message = data.split(' ')
    self.key = message[1]
    print 'New client created'
    print 'Type of Congestion Control: ' + self.key
    amount[self.key] = 0

    #check if a client of this key type already exists, in which case, don't create new graphing thread.
    try:
        value = client_types[self.key]
        client_types[self.key] += 1
        #don't create new graphing thread
    except KeyError:
        #client of this key type does not yet exist, create new graphing thread.
        client_types[self.key] = 1
        graph = Graph(self.key)
        graph.setDaemon(True) #TODO true or false?
        graph.start()

    self.client.send('* proceed ' + self.key)
    print 'New ' + self.key + ' client will commence sending data.'

    while self.running:
        try:
          data = self.client.recv(self.size)
        except socket.error:
          #socket closed on receive
          pass

        if data:
            amount[self.key] += len(data)
        else:
            amount[self.key] = 0
            self.client.close() #close socket
            self.running = 0
            graph.running = 0
            graph.join() #TODO join the graph thread?

if __name__ == "__main__":

  amount = {}
  client_types = {}
  
  try:
    port = sys.argv[1]
    num_comparisons = sys.argv[2]
  except:
    print '<port> <num_comparisons>'
    sys.exit(0)

  s = Server(int(port))
  t = threading.Thread(target = s.run)
  t.setDaemon(False)
  t.start()

'''
  b = BandwidthMonitor()    
  x = arange(0,100,1)
  y = []
   
  ion() #animated graphing

  while len(y) < 100:
    y.append(0)

  current_speed = 140
  line, = plot(x,y,'g')
  axis(array([0, 100, 0, current_speed]))

  xticks([])
  grid('on')
  title('TCP')
  ylabel('Throughput (MB)')
  xlabel('Time (s)')

  axis(array([0, 100, 0, 200]))

  while 1:
    b.initiate()
    time.sleep(1)
    b.terminate()
    speed = b.get_bandwidth()/(1000*1000) 

    if speed > current_speed:
        current_speed = speed + 40
	axis(array([0, 100, 0, current_speed]))

    print str(speed) + ' MBytes/second'
    y.pop(0)
    y.append(speed)
    line.set_ydata(y)
    draw()
'''