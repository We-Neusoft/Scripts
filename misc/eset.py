#!/usr/bin/python
import sys

from datetime import datetime

from ConfigParser import SafeConfigParser
from rarfile import RarFile
from signal import SIGTERM
from string import find, rfind
from time import mktime, strptime
from os import getpid, kill, makedirs, path, stat, unlink, utime
from urllib import urlretrieve, urlopen

import psycopg2

base_url = 'http://WE_CLOUD:WE_CLOUD@um01.eset.com/'
out_dir = '/data/www/eset/'
pid_file = '/var/run/eset.pid'

DATABASE = "dbname='eset' user='we'"

def download(filename, last_modified):
   file = out_dir + filename
   print 'Downloading: ' + filename
   sys.stdout.flush()
   try:
      urlretrieve(base_url + filename, file)
      utime(file, (last_modified, last_modified))
   except IOError:
      print 'Retrying:    ' + filename
      download(filename, last_modified)

def process(filename, size):
   if filename[rfind(filename, '/') + 1:] == 'update.ver':
      return

   dir = filename[:find(filename, '/')]
   if dir[rfind(dir, '-') + 1:] != 'sta':
      return

   try:
      handle = urlopen(base_url + filename)
      headers = handle.info()
      content_length = int(headers.getheader('Content-Length'))
      last_modified = mktime(strptime(headers.getheader('Last-Modified'), '%a, %d %b %Y %H:%M:%S %Z'))
   except IOError:
      print 'Retrying:    ' + filename
      process(filename, size)
      return

   if size != content_length:
      print 'Retrying:    ' + filename
      process(filename, size)
      return

   file = out_dir + filename
   if path.isfile(file):
      file_stat = stat(file)
      if (size == -1 or file_stat.st_size == size) and file_stat.st_mtime == last_modified:
         return

   dir = out_dir + filename[:rfind(filename, '/')]
   if not path.isdir(dir): 
      makedirs(dir)

   download(filename, last_modified)
   process(filename, size)

def fetch(version=''):
   # Download update.ver archive
   urlretrieve('http://update.eset.com/eset_upd/' + version + '/update.ver', '/tmp/' + version + '_update.ver.rar')

   # Extract update.ver
   RarFile('/tmp/' + version + '_update.ver.rar').extract('update.ver', path='/tmp/' + version)

   # Load update.ver
   config = SafeConfigParser()
   config.read('/tmp/' + version + '/update.ver')

   # Remove original host and expire section.
   config.remove_section('HOSTS')
   config.remove_section('Expire')

   # Force use my host
   config.add_section('HOSTS')
   config.set('HOSTS', 'Other', '200@http://WE_CLOUD/eset_upd/' + version)

   # Only fetch en-US and zh-CN
   for section in config.sections():
      if config.has_option(section, 'language'):
         if config.getint(section, 'language') != 1033 and config.getint(section, 'language') != 2052:
            config.remove_section(section)

   # Save update.ver
   with open(out_dir + 'eset_upd/' + version + '/update.ver', 'w') as ver_file:
      config.write(ver_file)

   # Process each file
   for section in config.sections():
      if config.has_option(section, 'file'):
         filename = config.get(section, 'file')
         if filename[:1] != '/':
            filename = '/eset_upd/' + version + '/' + filename

         dir = filename[1:find(filename, '/', 1)]
         if dir[rfind(dir, '-') + 1:] != 'sta':
            continue

         if config.has_option(section, 'size'):
            file_size = config.getint(section, 'size')
         else:
            file_size = -1

         if config.has_option(section, 'build'):
            file_build = config.getint(section, 'build')

            cursor.execute("SELECT * FROM eset WHERE file = '" + filename + "' AND build = " + str(file_build))
            if not cursor.rowcount:
               process(filename[1:], file_size)

               cursor.execute("UPDATE eset SET build = " + str(file_build) + " WHERE file = '" + filename + "'")
               if not cursor.rowcount:
                  cursor.execute("INSERT INTO eset (file, build) VALUES ('" + filename + "', " + str(file_build) + ")")

               db.commit()
         else:
            process(filename[1:], file_size)

if path.isfile(pid_file):
   with open(pid_file) as file:
      try:
         kill(int(file.read()), SIGTERM)
      except OSError:
         unlink(pid_file)

pid = str(getpid())
with open(pid_file, 'w') as file:
   file.write(pid)

db = psycopg2.connect(DATABASE)
cursor = db.cursor()

print datetime.now().isoformat() + ' - Start'

for version in ['', 'v4', 'v5', 'v6', 'v7', 'v5/pcu', 'v6/pcu', 'v7/pcu']:
   fetch(version)

print datetime.now().isoformat() + ' - Done'

cursor.close()
db.close()

unlink(pid_file)
