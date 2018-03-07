#!/usr/bin/env python

import subprocess
import re, time, os, sys
from optparse import OptionParser

class JStackSampler:

  def __init__(self, pid, loops, thread_filter):
    self.stacks = {}
    self.stacks_idx = []
    self.sample_cnt = loops
    self.pid = pid
    self.thread_filter = thread_filter

  def __sample_data(self):
    if os.getenv("JSTACK_CMD"):
      command=os.getenv("JSTACK_CMD") + " %d"
    else:
      command="/ib/tst_mobile/jdk1.8.0_60/bin/jstack %d"
    re_thread = re.compile("^\"(.*%s.*)\".*prio.*\]$" % (self.thread_filter))
    i=self.sample_cnt

    while(i>0):
      sys.stderr.write('. ')
      sys.stderr.flush()
      p = subprocess.Popen(command % (self.pid), bufsize=0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      is_stack = False
      stack_str = ""
      thread_name = None

      lines = p.stdout.readlines()
      p.stdout.close()
      for line in lines:
        m_thread_name = re_thread.match(line)
        if m_thread_name and not is_stack:
          is_stack = True
          thread_name = m_thread_name.groups()[0]
          if not thread_name in self.stacks.keys():
            self.stacks[thread_name] = {}
          continue

        if is_stack and thread_name:
          stack_str += line

        if line.strip() == "" and thread_name:
          if not self.stacks[thread_name].has_key(stack_str):
            self.stacks[thread_name][stack_str]=1
          else:
            self.stacks[thread_name][stack_str]+=1
          thread_name = None
          is_stack = False
          stack_str = ""

      i=i-1
      time.sleep(2.0)
    sys.stderr.write("\r")
    sys.stderr.flush()

  def __print_result(self):
    thread_stats = {}
    # sort stacks
    for thread in self.stacks.keys():
      if not thread in thread_stats.keys():
        thread_stats[thread] = {}
        thread_stats[thread]["count"] = 0
      for stack in self.stacks[thread].keys():
        thread_stats[thread]["count"] += self.stacks[thread][stack]
        self.stacks_idx.append("%d|%s|%s" % (self.stacks[thread][stack], thread, stack))

    for idx in sorted(self.stacks_idx, key=lambda x: int(x.split('|')[0])):
      data  = idx.split('|')
      print "Stats: %0.2f%% (%d/%d) THREAD: \"%s\" PID=%d" % (
        float(data[0])/thread_stats[data[1]]["count"]*100,
        int(data[0]), thread_stats[data[1]]["count"],
        data[1],
        self.pid)
      print "%s" % (data[2])

  def sampling(self):
    self.__sample_data()
    self.__print_result()

if __name__ == "__main__":
  usage = """
jStackProfiler sampled mittels JStack einen Java Process im interval von 2s. Danach werden die aufgetreten Stacktraces gezaehlt und sortiert.
Es kann ebenfalls ein filter angegeben werden, um nur gewisse Threads zu samplen.
Falls JSTACK_CMD gesetzt wird, so wird dieses als Kommand angezogen.
"""
  cmd_parser = OptionParser(usage=usage)
  cmd_parser.add_option("-p", "--pid", dest="pid", help="PID of the java process to sample")
  cmd_parser.add_option("-c", "--count", dest="loops", help="Number of loops to sample (wait time between is fixed to 2s), total runtime loops x wait time (2s)")
  cmd_parser.add_option("-f", "--filter", default="", dest="thread_filter", help="Thread name filter")

  (opts, args) = cmd_parser.parse_args()
  cmd_opts=vars(opts)

  sampler = JStackSampler(int(cmd_opts["pid"]), int(cmd_opts["loops"]), cmd_opts["thread_filter"])
  sampler.sampling()
