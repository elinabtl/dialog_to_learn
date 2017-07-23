import time
import imaplib
import re
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import server
import time
from test_pb2 import TestEmails
import google.protobuf.text_format

FROM_EMAIL  = "emailfilterclass1@gmail.com"
FROM_PWD  = "8uV8BGWwDibL"
SMTP_SERVER = "smtp.gmail.com"

EMAILS_DATA = TestEmails()

# Send 3 test emails - see the arrive properly
def sendTestEmail():
  try:

    with open('test.data', 'r') as f:
      test_data = f.read()
    google.protobuf.text_format.Merge(test_data, EMAILS_DATA)

    server = smtplib.SMTP(SMTP_SERVER, 587)
    server.starttls()
    server.login(FROM_EMAIL, FROM_PWD)

    print("Sending " + str(len(EMAILS_DATA.emails)) + " emails to test...")
    for email in EMAILS_DATA.emails:
      server.sendmail(FROM_EMAIL, email.to_email, composeEmail(email.subject, email.content, email.to_email))

  except Exception as e:
    print(str(e))
  finally:
    server.quit()

def composeEmail(subject, content, toEmail):
  msg = MIMEMultipart()
  msg['from'] = FROM_EMAIL
  msg['To'] = toEmail
  msg['Subject'] = subject
  msg.attach(MIMEText(content, 'plain'))
  return msg.as_string()

if __name__ == "__main__":
  sendTestEmail()
  time.sleep(3) # wait 3 seconds to let emails arrive
  server.main()
