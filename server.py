import sys
sys.path.insert(0,'/usr/local/lib/python3.6/site-packages')

import smtplib
import time
import imaplib
import email
import email.utils
import re
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import profanityfilter
from config_pb2 import Class
import google.protobuf.text_format

# Utility to read email from Gmail Using Python

# TODO:
# 1. If program crashes - close server connection. DONE
# 2. If handling an email fails - mark it as unread again.
# 3. Profanity filter + if there is a problem - don't send to the receiver - but to the teacher + add support for teacher (txt file) DONE
# 4. Change all the params passed to a class. DONE
# 5. Sending to a non-existing alias should return the email. DONE
# 6. Case sensitive for last and middle names... DONE
# 7. Change to protobuf DONE

FROM_EMAIL  = "emailfilterclass1@gmail.com"
FROM_PWD  = "8uV8BGWwDibL"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

PHONE_EMAIL_NAME_REGEX = r'((\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})|(\w+[.|\w])*@(\w+[.])*\w+|%s)'

# Global class data
CLASS_DATA = Class()

class EmailData:
  # All relevant data read from an email
  def __init__(self, sendData, aliasEmail):
    self.sendData = sendData
    self.aliasEmail = aliasEmail

class SendData:
  # All relevant data to send email
  def __init__(self, sendToEmail, subject, content):
    self.sendToEmail = sendToEmail
    self.subject = subject
    self.content = content

# Read the protobuf with the data
def readClassData():
  with open('config.data', 'r') as f:
    config_data = f.read()
  google.protobuf.text_format.Merge(config_data, CLASS_DATA)
  #import pdb; pdb.set_trace()
  # Code examples:
  # CLASS_DATA.teacher_email = 'aaa'
  # participant = CLASS_DATA.participants.add()
  # participant.real_email = 'bbb'
  # participant.alias_email = 'ccc'  

# Go over all the unread emails - and send the messages accordingly
def readEmailFromGmail():
  try:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(FROM_EMAIL,FROM_PWD)
    mail.select('inbox')

    type, data = mail.search(None, 'ALL', '(UNSEEN)')
    idList = data[0].split()

    # Print the count of all unread messages
    print(len(idList))
    print('\n')

    server = smtplib.SMTP(SMTP_SERVER, 587)
    server.starttls()
    server.login(FROM_EMAIL, FROM_PWD)

    for idx in idList:
      typ, data = mail.fetch(idx, '(RFC822)' )
      for response_part in data:
        if isinstance(response_part, tuple):
          msg = email.message_from_string(response_part[1])
          toRealEmail, message = composeEmail(readEmail(msg))
          server.sendmail(FROM_EMAIL, toRealEmail, message)

  except Exception as e:
    print(str(e))
  finally:
    server.quit()

def readEmail(msg):
  emailSubject = msg['subject']
  emailFrom = msg['from']
  emailTo = msg['to']
  emailContent = ''
  for part in msg.walk():
    if part.get_content_type() == "text/plain":
      emailContent = part.get_payload()
  lastName, demoEmail = findLastName(email.utils.parseaddr(emailFrom)[1])
  sendData = parseEmail(emailFrom, emailTo, emailSubject, emailContent, lastName)
  return EmailData(sendData, demoEmail)

def composeEmail(emailData):
  msg = MIMEMultipart()
  # Find the real destination email in csv:
  msg['from'] = FROM_EMAIL
  msg['To'] = emailData.sendData.sendToEmail
  msg['Subject'] = emailData.sendData.subject # couldn't change the from address to contain +name, so added reply to option
  msg.add_header('reply-to', emailData.aliasEmail)
  msg.attach(MIMEText(emailData.sendData.content, 'plain'))
  return emailData.sendData.sendToEmail, msg.as_string()

def findLastName(email):
  for user in CLASS_DATA.participants:
    if user.real_email==email:
      return user.last_name, user.alias_email
  return None

def findRealEmail(demoEmail):
  for user in CLASS_DATA.participants:
    if user.alias_email==demoEmail:
      return user.real_email
  return None

def parseEmail(emailFrom, emailTo, subject, content, lastName):
  # profanity filter from: https://pythonhosted.org/profanityfilter/
  regexp = re.compile(PHONE_EMAIL_NAME_REGEX%lastName)
  print(' From : ' + emailFrom)
  print(" To : " + emailTo)
  print(' Subject : ' + subject)
  print(' Content: ' + content)
  if regexp.search(content) or profanityfilter.is_profane(content) or regexp.search(subject) or profanityfilter.is_profane(subject):
    print(" Email or phone or last name or profanity in subject or content send to: " + CLASS_DATA.teacher_email + "\n")
    filteredSubject = profanityfilter.censor(re.sub(PHONE_EMAIL_NAME_REGEX%lastName, r'*CONTENT_PROBLEM*: \1', subject, flags=re.IGNORECASE))
    filteredContent = profanityfilter.censor(re.sub(PHONE_EMAIL_NAME_REGEX%lastName, r'*CONTENT_PROBLEM*: \1', content, flags=re.IGNORECASE))
    filteredSubject = "CONTENT_PROBLEM by " + email.utils.parseaddr(emailFrom)[1] + ": " + filteredSubject
    return SendData(CLASS_DATA.teacher_email, filteredSubject, filteredContent)
  else:
    parsedEmail = email.utils.parseaddr(emailTo)[1]
    realEmail = findRealEmail(parsedEmail)
    if realEmail == None:
      realEmail = email.utils.parseaddr(emailFrom)[1]
      subject = "Sent to wrong address (" + parsedEmail + "): " + subject
    return SendData(realEmail, subject, content)

if __name__ == "__main__":
  readClassData()
  readEmailFromGmail()