#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is an example script for mldonkey
#
# To use it you must telnet to mldonkey like this:
# telnet localhost 4000
# > auth user password
# > set file_completed_cmd "/path/to/this/script"
# > quit

import mlmanager

# Adjust some internal variables, for example add a text estension;
# You can also append to
# video_extensions, audio_extensions, cdimage_extensions and archive_extensions
mlmanager.text_extensions.append ("djvu")

# Change mail addr of the daemon and domain of the server.
mlmanager.domain = "example.org"
mlmanager.from_addr = "mldonkey@%s" % mlmanager.domain

# Set SMTP server (this is the default, but you could also use some external smtp
# server if it doesn't need authentication).
mlmanager.mail_server = "localhost" 

# Users that should be notified on error, default is "owner"
mlmanager.error_recipients = [ "owner", "admin@example.org" ]

# Incoming directory for your mldonkey downloads. Directory are not handled now
# This is the default so it really doesn't matter that you set it if it is
# /var/lib/mldonkey/incoming/files
mlmanager.files_incoming = "/var/lib/mldonkey/incoming/files"

# Our mldonkey supports auto commit so we don't need username and password, but we
# could also use download = mlmanager.Download(username = "user", password = "password")
download = mlmanager.Download()

# Start writing an email that will be sent to the right users at the end of
# the script
mail_text = "Download of %s completed.\n\n" % download.get_filename()

# Parse download duration. Ignore seconds because nobody cares about it.
hours, minutes, seconds = d.get_duration ()
if hours > 1:
    duration = "%s hours and %s minutes" % (hours, minutes)
elif hours == 1:
    duration = "one hour and %s minutes" % minutes
else:
    duration = "%s minutes" % minutes

# And add it to the text of email
mail_text += "Duration of the download: %s.\n\n" % duration

# Some users that need to be notified. "owner" means owner of the download
recipients = [ "user1@provider.com", "user2@anotherprovider.org" , "owner" ]

# Move download to the right place
if download.get_type() == "video":
    download.move("/shared/Films")
    mail_text += "The file has been recognized as a film so it has been copied\n"
    mail_text += "in /shared/Films.\n"

elif download.get_type() == "audio":
    download.move("/shared/Musica")
    mail_text += "The file has been recognized as music so it has been copied\n"
    mail_text += "in /shared/Music.\n"
    
    # Our friend likes music, so copy this in his home directory (mldonkey must have
    # permission to write there!
    download.copy ("/home/friend/")

else:
    download.move("/shared")
    mail_text += "The file has not been automagically recognized, so it is\n"
    mail_text += "in /shared waiting for someone to put it in the right place.\n"

if download.is_in_group("remote"):
    mail_text += "The file will be transfered to a remote server.\n"

    
    # user2 is not interested in files that need to be transferred
    recipients.remove("user2@anotherprovider.org")

# Script signature
mail_text += "\nmldonkey <mldonkey@robol.it>\n"

# Notify users by mail
download.notify_email(recipients, 
                      "Download of %s completed" % download.get_filename(), 
                      mail_text)


# Finally transfer the file. This is a blocking call, so leave at the end after
# mail sending. 
if download.is_in_group("remote"):
    download.rsync("user@remote_server.org:myfolder/downloads/")

