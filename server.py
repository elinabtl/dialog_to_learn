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
from config_pb2 import Classes
import google.protobuf.text_format
from difflib import Differ

# Utility to read email from Gmail Using Python

# TODO:
# 1. If program crashes - close server connection. DONE
# 2. If handling an email fails - mark it as unread again.
# 3. Profanity filter + if there is a problem - don't send to the receiver - but to the teacher + add support for teacher (txt file) DONE
# 4. Change all the params passed to a class. DONE
# 5. Sending to a non-existing alias should return the email. DONE
# 6. Case sensitive for last and middle names... DONE
# 7. Change to protobuf DONE

# FROM_EMAIL  = "emailfilterclass1@gmail.com"
# FROM_PWD  = "8uV8BGWwDibL"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

PHONE_EMAIL_NAME_REGEX = r'((\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})|(\w+[.|\w])*@(\w+[.])*\w+|%s)'

# Global class data
CLASS_DATA = Classes()

class EmailData:
  # All relevant data read from an email
  def __init__(self, sendData, aliasEmail, classIndex):
    self.sendData = sendData
    self.aliasEmail = aliasEmail
    self.classIndex = classIndex

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
  for classIndex, currentClass in enumerate(CLASS_DATA.classes):
    try:
      mail = imaplib.IMAP4_SSL(IMAP_SERVER)
      mail.login(currentClass.class_email,currentClass.class_pwd)
      mail.select('inbox')

      type, data = mail.search(None, 'ALL', '(UNSEEN)')
      idList = data[0].split()

      # Print the count of all unread messages
      print("<<<Class: " + currentClass.class_email + " , unread emails: " + str(len(idList)) + ">>>\n")

      server = smtplib.SMTP(SMTP_SERVER, 587)
      server.starttls()
      server.login(currentClass.class_email, currentClass.class_pwd)

      for idx in idList:
        typ, data = mail.fetch(idx, '(RFC822)' )
        for response_part in data:
          if isinstance(response_part, tuple):
            msg = email.message_from_string(response_part[1].decode('utf-8'))
            emailData = readEmail(msg, classIndex)
            if emailData != None:
              toRealEmail, message = composeEmail(emailData)
              server.sendmail(currentClass.class_email, toRealEmail, message)
              print("Sending email to " + toRealEmail + "\n")
            else:
              print("Email was from unrecognized account: " + msg['from'] + "\n")

    except Exception as e:
      print(str(e))

    finally:
      server.quit()

def readEmail(msg, classIndex):
  emailSubject = msg['subject']
  emailFrom = msg['from']
  emailTo = msg['to']
  emailContent = ''
  for part in msg.walk():
    if part.get_content_type() == "text/plain":
      emailContent = part.get_payload()
  lastName, demoEmail = findLastName(email.utils.parseaddr(emailFrom)[1], classIndex)
  if lastName==None and demoEmail==None:
    return None
  sendData = parseEmail(emailFrom, emailTo, emailSubject, emailContent, lastName, classIndex)
  return EmailData(sendData, demoEmail, classIndex)

def composeEmail(emailData):
  msg = MIMEMultipart()
  # Find the real destination email in csv:
  msg['from'] = CLASS_DATA.classes[emailData.classIndex].class_email
  msg['To'] = emailData.sendData.sendToEmail
  msg['Subject'] = emailData.sendData.subject # couldn't change the from address to contain +name, so added reply to option
  msg.add_header('reply-to', emailData.aliasEmail)
  msg.attach(MIMEText(emailData.sendData.content, 'plain'))
  return emailData.sendData.sendToEmail, msg.as_string()

def findLastName(email, classIndex):
  for user in CLASS_DATA.classes[classIndex].participants:
    if user.real_email==email:
      return user.last_name, user.alias_email
  return None, None

def findRealEmail(demoEmail, classIndex):
  for user in CLASS_DATA.classes[classIndex].participants:
    if user.alias_email==demoEmail:
      return user.real_email
  return None

def appendCensoredToText(input_text, censored_text):
  l1 = input_text.split(' ')
  l2 = censored_text.split(' ')
  dif = list(Differ().compare(l1, l2))
  return " ".join([i[2:] if i[:1] == '-' or i[:1] == '+' else i[2:] for i in dif])

def parseEmail(emailFrom, emailTo, subject, content, lastName, classIndex):
  # profanity filter from: https://pythonhosted.org/profanityfilter/
  regexp = re.compile(PHONE_EMAIL_NAME_REGEX%lastName)
  print(' From : ' + emailFrom)
  print(" To : " + emailTo)
  print(' Subject : ' + subject)
  print(' Content: ' + content)
  if regexp.search(content) or profanityfilter.is_profane(content) or regexp.search(subject) or profanityfilter.is_profane(subject):
    print(" Email or phone or last name or profanity in subject or content send to: " + CLASS_DATA.classes[classIndex].teacher_email)
    censoredSubject = profanityfilter.censor(subject)
    censoredContent = profanityfilter.censor(content)
    censoredSubject = appendCensoredToText(subject, censoredSubject)
    censoredContent = appendCensoredToText(content, censoredContent)
    filteredSubject = re.sub(PHONE_EMAIL_NAME_REGEX%lastName, r'*CONTENT_PROBLEM*: \1', censoredSubject, flags=re.IGNORECASE)
    filteredContent = re.sub(PHONE_EMAIL_NAME_REGEX%lastName, r'*CONTENT_PROBLEM*: \1', censoredContent, flags=re.IGNORECASE)
    filteredSubject = "CONTENT_PROBLEM by " + email.utils.parseaddr(emailFrom)[1] + ": " + filteredSubject
    return SendData(CLASS_DATA.classes[classIndex].teacher_email, filteredSubject, filteredContent)
  else:
    parsedEmail = email.utils.parseaddr(emailTo)[1]
    realEmail = findRealEmail(parsedEmail, classIndex)
    if realEmail == None:
      realEmail = email.utils.parseaddr(emailFrom)[1]
      subject = "Sent to wrong address (" + parsedEmail + "): " + subject
      print(" Email received with incorrect alias, returning to sender.")
    return SendData(realEmail, subject, content)

def main():
  readClassData()
  readEmailFromGmail()

if __name__ == "__main__":
  main()
