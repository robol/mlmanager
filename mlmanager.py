#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This is mlmanager, a python script thought to handle
# downloaded file from mldonkey. 
#
# It is released under the GNU Public License 3
#
# Leonardo Robol <leo@robol.it>

__author__ = "Leonardo Robol <leo@robol.it>"

import os, sys, socket, shutil, subprocess, time

# Set file extensions to match. 
video_extensions = ['avi', 'mpeg', 'mpg', 'mkv', 'm2v', 'divx', 'xvid']
audio_extensions = ['mp3,' 'ogg', 'wav', 'flac', 'aac' ]
text_extensions  = ['pdf', 'doc', 'odt', 'ods', 'odp', 'ppt', 'rtf',
		    'pps', 'xls' , 'txt' ]
cdimage_extensions = [ 'iso', 'nrg' ]

class FileType():
  """
  This class represent the type of a file, i.e you
  can check if it is a video, a text, an image...
  """
  
  def __init__(self, filename):
    self._filename = filename
    self._detect_type ()
    
    
  def _test_extension(self, extension):
    return self._filename.lower().endswith(extension)
    
  def _detect_type(self):
    """Detect the type of the file and save it in the internal
    varaible _type"""
    if len(filter(self._test_extension, video_extensions)) > 0:
      self._type = "video"
    elif len(filter(self._test_extension, audio_extensions)) > 0:
      self._type = "audio"
    elif len(filter(self._test_extension, text_extensions)) > 0:
      self._type = "text"
    elif len(filter(self._test_extension, cdimage_extensions)) > 0:
      self._type = "cdimage"
    else:
      self._type = "other"
    
  def is_video(self):
    return (self._type == "video")
    
  def is_image(self):
    return (self._type == "audio")
    
  def is_text(self):
    return (self._type == "text")
  
  def is_cdimage(self):
    return (self._type == "cdimage")
    
  def __str__(self):
    return self._type
    
  def __repr__(self):
    return "<FileType '%s'>" % self._type
  

class Download():
  """
  This class represent a file or a folder downloaded via mldonkey.
  You should create an instance of this calling
  
    d = Download("path/to/file")
    
  and you should be able to perform your processing with some useful
  methods
  """
  
  def __init__(self, username, password, filename = None, group = None):
    """Perform some heuristic to determine the filetype,
    filename, groups and similar"""
    
    # Set username and password
    self._username = username
    self._password = password
    
    self._filename = filename
    self._group = group
    
    # If filename is not set then we can recover it
    # from the environment variables.
    if self._filename is None:
      self._filename = os.getenv("FILENAME")
    
      
    # Recover other data from environment
    if not self._group:
      self._group = os.getenv("FILE_GROUP")
      
    self._owner = os.getenv("FILE_OWNER")
    self._incoming = os.getenv("INCOMING")
    
    # The file is not yet committed. You will need to commit it
    # before trying to move it.
    self._committed = False
    
    # Construct the path of the file; this will be the real
    # path after it will be committed!
    self._dest_path = self._incoming
    if not self._dest_path.endswith(os.path.sep):
      self._dest_path += os.path.sep
    self._dest_path += self._filename
    
    self._type = FileType(self._filename)
    
  def __repr__(self):
    return "<Download '%s'>" % self._filename
    
  def _authentication_command (self):
    return "auth %s %s" % (self._username, self._password)
    
  def commit(self):
    """Commit the file, i.e. save it to the hard disk
    in its final position. This should be the first 
    thing you do"""
    
    commands = [ self._authentication_command (), 
		 "commit" ]
    self.send_command (commands)
    self._committed = True
    
    
  def send_command(self, command_list):
    """You can send a command, or a list of command
    to the daemon. Note that the every call to this
    function will open a connection to the daemon, so
    you will need to authenticate every time.
    """
    if isinstance(command_list, str):
      command_list = [ command_list ]
      
    # Open the connection
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.connect(("localhost", 4001))
    except Exception, e:
      raise RuntimeError("Unable to connect to mldonkey daemon: %s" % e)
    
    # Costruct the command line
    command_line = "\n".join(command_list)
    # and execute it
    s.send(command_line + "\n")
    
    # Cleanup
    s.send("quit\n")
    s.close ()
    
  def move(self, destination_folder, filename = None):
    """Move the file to destination. destination_folder MUST be
    a folder. You could change the filename with the optional 
    filename parameter"""
    
    if not filename:
      filename = self._filename
    
    # Assicuriamoci che il file sia stato creato
    if not self._committed:
      self.commit ()
      
    # Be sure that this is a directory
    if not destination_folder.endswith(os.path.sep):
      destination_folder += os.path.sep
      
    shutil.move (self._dest_path, destination_folder + filename)
    
    # Update _dest_path
    self._dest_path = destination_folder + filename
    
  def rsync(self, remote_destination):
    """Rsync the file to the remote destination. There must be an ssh key
    in the remote server otherwise nothing will happen. The script will
    automatically try a bunch of time to retransfer the file if 
    the connection fail."""
    if not self._committed:
      self.commit ()
      
    # Initialize internal counter of the times we have tried to move the file
    self._rsync_counter = 0
    s = subprocess.Popen("rsync --partial -az --compress-level=9 \"%s\" \"%s\"" % (self._dest_path,
									   remote_destination),
			shell = True, stderr = subprocess.PIPE, stdout = subprocess.PIPE)
    ret_code = s.wait ()
    
    # If we fail call this funtion recursively to retry...wait for 5 seconds and the go (it could
    # be only a network problem)
    if ret_code != 0:
      self._rsync_counter += 1
      if self._rsync_counter < 5:
	time.sleep (5)
	self.rsync(remote_destination)
      else:
	self.notify_error("Rsync transfer of file %s failed more than 5 times, aborting" % self._filename)
	
  def notify_error(self, message):
    """Notify error via email"""
    pass
  
  def notify_email(self, recipients, message):
    """Notify something to some people via email"""
    pass
    
  def get_type(self):
    """
    Return the type of the selected file, it could be 
    Video, Audio, Image or Other, if none matches.
    """
    return str(self._type)


