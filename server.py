import smtplib
import time
import imaplib
import email
import email.utils
import re
import csv
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from config_pb2 import Class

# Utility to read email from Gmail Using Python

# TODO:
# 1. If program crashes - close server connection.
# 2. If handling an email fails - mark it as unread again.
# 3. Profanity filter + if there is a problem - don't send to the receiver - but to the teacher + add support for teacher (txt file)
# 4. Change all the params passed to a class.
# 5. Sending to a non-existing alias should return the email.
# 6. Case sensitive for last and middle names...

FROM_EMAIL  = "emailfilterclass1@gmail.com"
FROM_PWD  = "8uV8BGWwDibL"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

PHONE_REGEX = '(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})'
EMAIL_REGEX = '(\w+[.|\w])*@(\w+[.])*\w+'

# Global for the csv
USERS_LIST = None

# Read the csv with the data
def readUsersList():
  class1 = Class()
  with open('users_list.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    users = list(reader)
  return users

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
          sendSubject, sendContent, emailTo, demoEmail = readEmail(msg)
          toRealEmail, message = composeEmail(sendSubject, sendContent, emailTo, demoEmail)
          server.sendmail(FROM_EMAIL, toRealEmail, message)

  except Exception, e:
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
  sendSubject, sendContent = parseEmail(emailFrom, emailTo, emailSubject, emailContent, lastName)
  return sendSubject, sendContent, emailTo, demoEmail

def composeEmail(sendSubject, sendContent, emailTo, demoEmail):
  msg = MIMEMultipart()
  # Find the real destination email in csv:
  toRealEmail = findRealEmail(email.utils.parseaddr(emailTo)[1])
  msg['from'] = FROM_EMAIL
  msg['To'] = toRealEmail
  msg['Subject'] = sendSubject # couldn't change the from address to contain +name, so added reply to option
  msg.add_header('reply-to', demoEmail)
  msg.attach(MIMEText(sendContent, 'plain'))
  return toRealEmail, msg.as_string()

def findLastName(email):
  for user in USERS_LIST:
    if user['realEmail']==email:
      return user['lastName'], user['demoEmail']
  return None

def findRealEmail(demoEmail):
  for user in USERS_LIST:
    if user['demoEmail']==demoEmail:
      return user['realEmail']
  return None

def parseEmail(emailFrom, emailTo, subject, content, lastName):
  contentNoPhone = re.sub(PHONE_REGEX, "*PHONE*", content)
  contentFinal = re.sub(EMAIL_REGEX, "*EMAIL*", contentNoPhone)
  contentFinal = contentFinal.replace(lastName, "*LAST_NAME*")
  subjectNoPhone = re.sub(PHONE_REGEX, "*PHONE*", subject)
  subjectFinal = re.sub(EMAIL_REGEX, "*EMAIL*", subjectNoPhone)
  subjectFinal = subjectFinal.replace(lastName, "*LAST_NAME*")
  print(' From : ' + emailFrom)
  print(" To : " + emailTo)
  print(' Subject : ' + subjectFinal)
  print(' Content: ' + contentFinal)
  print('\n')
  return subjectFinal, contentFinal

if __name__ == "__main__":
  USERS_LIST = readUsersList()
  readEmailFromGmail()