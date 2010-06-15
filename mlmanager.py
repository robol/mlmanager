# -*- coding: utf-8 -*-
#
# mlmanager is a python package that aims to "organize"
# your mldonkey downloads. 
#
# You can easily write a script that take care of moving
# a file in the right place and to write emails to the right
# people that need to know about the download. 
#
#
# It is released under the GNU General Public License Version 3
#
# Author: Leonardo Robol <leo@robol.it>


#
# START OF CONFIGURATION SECTION
#

# The fully qualified (or not fully qualified - it really doesn't matter)
# domain that the server is part of. 
domain = "robol.it"

# This is the mail address that will be set as sender for all
# the emails generated by the script.
from_addr = "mldonkey <mldonkey@%s>" % domain

# Mail server that the script will use to deliver emails. It must be properly 
# configured to relay mail from the domain selected.
mail_server = "localhost"

# Users that should be notified when an error occurs in the script. You
# can use the wildcard "owner" to match the owner of the file downladed. 
# This is generally true for every email function in mlmanager
error_recipients = [ "owner" ]

# Number of times that rsync should try to transfer the file before
# giving up.
rsync_tries = 5

# Directory in which files are stored.
files_incoming = "/removable/data/mldonkey/incoming/files"

# Set file extensions to match. You can add extensions in every category
video_extensions   = ['avi', 'mpeg', 'mpg', 'mkv', 'm2v', 'divx', 'xvid']
audio_extensions   = ['mp3', 'ogg', 'wav', 'flac', 'aac' ]
text_extensions    = ['pdf', 'doc', 'odt', 'ods', 'odp', 'ppt', 'rtf',
		      'pps', 'xls' , 'txt' ]
cdimage_extensions = [ 'iso', 'nrg' ]
archive_extensions = [ 'rar', 'zip', '7z', 'tar.gz', 'tar.bz2', 'lzo' ]


#
# END OF CONFIGURATION
#
#
# START OF CODE
#

__author__ = "Leonardo Robol <leo@robol.it>"

import os, sys, socket, shutil, subprocess, time, smtplib
from email.mime.text import MIMEText

class FileType():
  """
  This class represent the type of a file, i.e you
  can check if it is a video, a text, an image...
  It can be:
   - video
   - audio
   - text
   - archive
   - other
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
    elif len(filter(self._test_extension, archive_extensions)) > 0:
      self._type = "archive"
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
    
  def is_archive(self):
    return (self._type == "archive")
    
  def __str__(self):
    return self._type
    
  def __repr__(self):
    return "<FileType '%s'>" % self._type
  

class Download():
  """
  This class represent a file or a folder downloaded via mldonkey.
  You should create an instance of this calling
  
    d = Download()
  
  or, if you want
  
    d = Download(username = "admin", password = "mysecretpassword")
    
  This allow the script to connect to the mldonkey daemon and ensure
  that the file have been committed. It is not needed for mldonkey
  >= 2.7, but IT IS REQUIRED if you run an earlier mldonkey!
  """
  
  def __init__(self, username = None, password = None, filename = None, group = None):
    """Perform some heuristic to determine the filetype,
    filename, groups and similar"""
    
    # Set username and password
    self._username = username
    self._password = password
    
    # If you do not provide username or password we can't
    # execute any command
    if not self._username or not self._password:
      self._authentication_available = False
    
    self._filename = filename
    self._group = group
    
    # If filename is not set then we can recover it
    # from the environment variables.
    if self._filename is None:
      self._filename = os.getenv("FILENAME")
      
    # La durata del download in secondi
    self._duration = os.getenv("DURATION")
      
    # Recover other data from environment
    if not self._group:
      self._group = os.getenv("FILE_GROUP")
      
    self._owner = os.getenv("FILE_OWNER")
    self._incoming = files_incoming
    
    self._user_email = os.getenv("USER_EMAIL")
    
    # The file is not yet committed. You will need to commit it
    # before trying to move it. If we do not have authentication
    # assume that auto commit is enabled
    self._committed = False
    if not self._authentication_available:
      self._committed = True
    
    # Construct the path of the file; this will be the real
    # path after it will be committed!
    self._dest_path = self._incoming
    if not self._dest_path.endswith(os.path.sep):
      self._dest_path += os.path.sep
    self._dest_path += self._filename
    
    try:
      self._type = FileType(self._filename)
    except Exception, e:
      self._type = "other"    

    
  def __repr__(self):
    return "<Download '%s'>" % self._filename
    
  def _authentication_command (self):
    if not self._authentication_available:
      self._notify_error("Authentication data is not available, I can't authenticate to mldonkey")
      return None
    return "auth %s %s" % (self._username, self._password)
    
  def commit(self):
    """Commit the file, i.e. save it to the hard disk
    in its final position. This should be the first 
    thing you do"""
    
    authentication = self._authentication_command ()
    if not authentication:
      return None
    
    commands = [ authentication, 
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
      s.connect(("localhost", 4000))
    except Exception, e:
      self._notify_error("Unable to connect to mldonkey daemon: %s" % e)
    
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
      
    f = open("/rw/env", "w")
    f.write(str(self._incoming))
    f.close ()
      
    # Be sure that this is a directory
    if not destination_folder.endswith(os.path.sep):
      destination_folder += os.path.sep
      
    shutil.move (self._dest_path, destination_folder + filename)
    
    # Update _dest_path
    self._dest_path = destination_folder + filename
    
  def copy(self, destination, track = False):
    """
    Copy the file to another destination. Destination could be a folder
    to move the file in, or a complete path. The script will keep track
    only of the original file, i.e. if you call move() it will move the 
    original file; if this is not what you want, move() the file to the
    right location and then copy() it around."""
    
    if not self._committed:
      self.commit()
    shutil.copy(self._dest_path, destination)
    
    
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
    
    # If we fail call this funtion recursively to retry...wait for 60 seconds and then go (it could
    # be only a network problem)
    if ret_code != 0:
      self._rsync_counter += 1
      if self._rsync_counter < rsync_tries:
	time.sleep (60)
	self.rsync(remote_destination)
      else:
	self._notify_error("Rsync transfer of file %s failed more than 5 times, aborting" % self._filename)
	
  def _notify_error(self, message):
    """Notify error via email"""
    self._send_mail (error_recipients, "[mlmanager] An error occurred",
		     message)
  
  def notify_email(self, recipients, subject, message):
    """Notify something to some people via email"""
    self._send_email (recipients, subject, message)
  
  def _send_email(self, recipients, subject, message):
    """Low level function to send an e-mail."""
    
    msg = MIMEText(message)
    msg.set_charset ("utf-8")
    msg['From'] = from_addr
    
    # If recipients is a string make it a list
    if isinstance(recipients, str):
      recipients = [ recipients ]
      
    # Add user email if requested
    if "owner" in recipients:
      recipients.remove("owner")
      recipients.append(self._user_email)
      
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    
    # Obtain message data
    data = msg.as_string ()
    
    # Open a connection to the SMTP server
    try:
      s = smtplib.SMTP( host = mail_server )
      s.sendmail (from_addr, recipients, data)
      s.quit ()
    except Exception, e:
      raise RuntimeError("Error while notifying you of an error: %s" % e)
    
  def is_in_group(self, group):
    """Return True if file is part of the selected group,
    False otherwise"""
    return (self._group == group)
    
    
  def get_type(self):
    """
    Return the type of the selected file, it could be 
    video, audio, image, cdimage, archive or other, if none matches.
    """
    return str(self._type)
    
  def get_filename(self):
    return self._filename
    
  def get_duration(self):
    """
    Obtain the duration as a tuple (hours, minutes, seconds)
    """
    d = int(self._duration)
    seconds = d % 60
    minutes = (d - seconds)/60 % 60
    hours = (d - seconds - 60*minutes)/3600
    
    return (hours, minutes, seconds)

