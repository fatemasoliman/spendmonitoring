import pandas as pd
import numpy as np


#READ IN YESTERYDA'S SPENDS, BUDGET SETTINGS, AND TRADER LOOKUP
spends=pd.read_csv('144170621.csv', sep=',',header=0, encoding='latin-1') 
lisettings= pd.read_csv('line_items.csv', sep=',',header=0, encoding='latin-1')
traders=pd.read_csv('gmt_traders.csv', sep=',',header=0, encoding='latin-1')

ydaygmt=pd.read_csv('ydaygmt.csv', sep=',',header=0, encoding='latin-1')

#PIVOT SPENDS AND SUM COST
ioSpends = pd.pivot_table(spends, values=['Total Media Cost (Advertiser Currency)'], 
	index=['Insertion Order'], aggfunc=np.sum)


#TURN PIVOT INTO DF, RESET INDEX TO HAVE IO NAME AS A COLUMN, NAME COLUMNS
ioSpends = pd.DataFrame(data=ioSpends)
ioSpends.reset_index(level=0, inplace=True)
ioSpends.columns=['Insertion Order', 'Total Media Cost']



#PIVOT LINE ITEM SETTINGS - AVERAGE OF IO BUDGET NOT SUM, CREATE DF AND RESET INDEX, NAME COLUMNS
ioBudgets= pd.pivot_table(lisettings, values=['Io Pacing Amount'], index=['Io Name'], aggfunc=np.average)
ioBudgets = pd.DataFrame(data=ioBudgets)
ioBudgets.reset_index(level=0, inplace=True)
ioBudgets.columns=['Insertion Order', 'Budget']


#MERGE SPENDS AND BUDGETS BASED ON IO NAME
allIO = ioSpends.merge(ioBudgets, on='Insertion Order', how='left')

#CREATE IO HIT CAP FIELD 
allIO['hitCap'] = allIO.values[:,1]>=allIO.values[:,2]

#CREATE CAPPED IOS DF
cappedIO =allIO.loc[allIO['hitCap'] == True]
cappedIO =cappedIO.loc[cappedIO['Budget']>0]

cappedIO = cappedIO.merge(ydaygmt, on='Insertion Order', how = 'left')

cappedIO = cappedIO[['Insertion Order', 'Total Media Cost_x', 'Budget_x', 'hitCap_x', 'Tally']]
cappedIO.columns = ['Insertion Order', 'Total Media Cost', 'Budget', 'hitCap', 'Tally']

#########

cappedIO['TallyBool'] = cappedIO['Insertion Order'].isin(ydaygmt['Insertion Order'])

cappedIO['Tally']= np.where(cappedIO['TallyBool']==True, cappedIO['Tally']+1, 0)

cappedIO.Tally = cappedIO.Tally.astype(int)
###########


cappedIO=cappedIO.merge(traders, on='Insertion Order', how='left')

print(cappedIO)

####
cappedIO.to_csv('ydaygmt.csv')
#######

liSpends = pd.pivot_table(spends, values=['Total Media Cost (Advertiser Currency)'], 
	index=['Line Item ID'], aggfunc=np.sum)

liSpends = pd.DataFrame(data=liSpends)
liSpends.reset_index(level=0, inplace=True)
liSpends.columns = ['Line Item Id', 'Total Media Cost']


liNames = lisettings[['Line Item Id', 'Advertiser Name', 'Io Name', 'Line Item Name']].copy()
liNames.columns=['Line Item Id', 'Advertiser Name', 'Insertion Order', 'Line Item Name']


liBudgets= pd.pivot_table(lisettings, values=['Line Item Pacing Amount'], index=['Line Item Id'], aggfunc=np.average)
liBudgets = pd.DataFrame(data=liBudgets)
liBudgets.reset_index(level=0, inplace=True)
liBudgets.columns=['Line Item Id', 'Budget']

liBudgets = liNames.merge(liBudgets, on='Line Item Id', how='left')

allLI = liBudgets.merge(liSpends, on='Line Item Id', how='left')

#print(list(allLI))
allLI['hitCap'] = allLI.values[:,5]>=allLI.values[:,4]

cappedLI =allLI.loc[allLI['hitCap'] == True]

cappedLI =cappedLI.loc[cappedLI['Budget']>0]

cappedLI=cappedLI.merge(traders, on='Insertion Order', how='left')


#EMAIL TRADERS THEIR CAMPAIGNS THAT HIT BUDGET CAPS
# A LOT OF THIS PART WAS ADAPTED FROM https://medium.freecodecamp.org/send-emails-using-code-4fcea9df63f

import smtplib

from string import Template

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

MY_ADDRESS = ''
PASSWORD = ''

def get_contacts(filename):
    """
    Return two lists names, emails containing names and email addresses
    read from a file specified by filename.
    """
    
    names = []
    emails = []
    with open(filename, mode='r', encoding='utf-8') as contacts_file:
        for a_contact in contacts_file:
            names.append(a_contact.split(',')[0])
            emails.append(a_contact.split(',')[1])
    return names, emails

def read_template(filename):
    """
    Returns a Template object comprising the contents of the 
    file specified by filename.
    """
    
    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)

def main():
    names, emails = get_contacts('gmtcontacts.txt') # read contacts
    message_template = read_template('message.txt')

    # set up the SMTP server
    s = smtplib.SMTP(host='smtp.gmail.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # For each contact, send the email:
    for name, email in zip(names, emails):
        msg = MIMEMultipart()       # create a message
        traderCappedIO = pd.DataFrame(data=cappedIO.loc[cappedIO['Trader']==name])
        traderCappedIO=traderCappedIO.sort_values(by='Budget', ascending=False)
        traderCappedIO=traderCappedIO[['Tally','Budget', 'Insertion Order']]
        #traderCappedIO=traderCappedIO[['Budget', 'Insertion Order']]
        
        traderCappedIO= traderCappedIO.to_string(index=False)
        if "Empty DataFrame" in traderCappedIO:
            traderCappedIO="None"

        traderCappedLI = pd.DataFrame(data=cappedLI.loc[cappedLI['Trader']==name])
        traderCappedLI=traderCappedLI.sort_values(by='Budget', ascending=False)
        traderCappedLI=traderCappedLI[['Budget', 'Line Item Name']]
        traderCappedLI=traderCappedLI.to_string(index=False)

        if "Empty DataFrame" in traderCappedLI:
            traderCappedLI="None"

        # add in the actual person name to the message template
        message = message_template.substitute(PERSON_NAME=name.title(),IO_Caps=traderCappedIO, LI_Caps=traderCappedLI)

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From']=MY_ADDRESS
        msg['To']=email
        msg['Subject']="DBM Spend Monitoring"
        
        # add in the message body
        msg.attach(MIMEText(message, 'plain'))
        
        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg
        
    # Terminate the SMTP session and close the connection
    s.quit()
if __name__ == '__main__':
    main()