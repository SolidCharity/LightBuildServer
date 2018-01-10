#!/usr/bin/env python3
"""Test: sending an email via port 587"""

# Copyright (c) 2014-2018 Timotheus Pokorra <tp@tbits.net>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA
#

import smtplib
from smtplib import SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
import Config

def email(fromAddress, toAddress, subject):
    msg = MIMEText(("<html><body>Test</body></html>").encode('utf-8'), 'html','utf-8')
    msg['From'] = fromAddress
    msg['To'] = toAddress
    msg['Subject'] = subject

    # collect the configuration
    config = Config.LoadConfig()
    emailserver = config['lbs']['EmailServer']
    emailport = config['lbs']['EmailPort']
    emailuser = config['lbs']['EmailUser']
    emailpassword = config['lbs']['EmailPassword']

    # Send the mail
    server = smtplib.SMTP(host=emailserver, port=emailport, timeout=10)
    TO = [toAddress] # must be a list
    try:
      server.set_debuglevel(1)
      server.ehlo()
      server.starttls()
      server.login(emailuser, emailpassword)
      server.sendmail(fromAddress, TO, msg.as_string())
    finally:
      server.quit()

email("noreply.lbs@example.org", "test@example.org", "test")
