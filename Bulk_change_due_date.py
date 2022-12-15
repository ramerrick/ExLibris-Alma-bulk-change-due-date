#!/usr/bin/env python
# coding: utf-8

#Bulk change due date script.
#Authors: Rachel Merrick and John Eliot.
#Scripts using a GET request to retrieve an Alma anlytics report of loans that need the due date changed.
#A PUT request for each loan is sent to Alma to change the due date to one specified in the script.

#Import libraries and modules
import requests as req #Used to to access Alma API.
from requests.structures import CaseInsensitiveDict #used to create and send JSON loan object.
import xml.etree.ElementTree as ET #Used to parse XML file.
import pandas as pd #Used to create data frame
import re #Allows use of regular expresions which have been used to extract error messages.

#SET VARIABLES
analyatics_path = "add your path" #Path where report lives in analytics
analytics_key = 'add your key'#analytics production key
api_key = 'add your key' #Alma user production API key 
due_date = '2023-01-06T12:59:00Z' #Use during daylight savings time.
#due_date = '2023-01-06T13:59:00Z' #Use outside of daylight savings time.

#Declare method get attributes which interates over XML root and adds all instances of an attribute to a list.
#The list is then returned.
def get_attribute(attribute, root):
    #Create empty list
    All_values = []
    #interate over the XML root by attribute
    for attribute in root.iter(attribute):
        #append values to list.
        All_values.append(attribute.text)
    #return list of attributes.
    return All_values

#Build analytics API get URL.
analytics_url = ('https://api-eu.hosted.exlibrisgroup.com/almaws/v1/analytics/reports?path='
                     +analyatics_path+'&limit=1000&col_names=true&apikey=' + analytics_key)
#Send analytics get request.
analytics_response = req.get(analytics_url)

#writting analytics report (API repsonse) to xml file.
response_xmlfile = open('bulk_renew_analytics.xml', 'w') #Open file in write mode.
response_xmlfile.write(analytics_response.text) #write to file.
response_xmlfile.close() #Close file.   

#Declaring XML tree and root from analytics report.
tree = ET.parse('bulk_renew_analytics.xml')
root = tree.getroot()

#Create a set of lists of each attribute from the analytics report.
loan_ID_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column3', root)
due_date_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column2', root)
loans_status_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column4', root)
location_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column5', root)
identifier_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column6', root)
user_group_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column7', root)
barcode_list = get_attribute('{urn:schemas-microsoft-com:xml-analysis:rowset}Column1', root)

#If nothing analytics report, print no results statement and skip the rest of the script.
if len(identifier_list) == 0:
        print('Analytics report has no results')

# else proceed to change due dates.
else:
        #Create data frame to record changes and errors.
        df_data = {'Primary ID' : identifier_list , 'Loan ID' : loan_ID_list, 'Barcode' : barcode_list, 
                   'Loan status' : loans_status_list, 'Due date' : due_date_list, 'User group' : user_group_list, 
                   'Note' : location_list } #Build dictionary for creating the dataframe
        df = pd.DataFrame(df_data, columns=['Primary ID' , 'Loan ID', 'Barcode',
                                            'Loan status', 'Due date', 'User group', 'Note'] )#Create dataframe

        #Setting variables that will be used to build  API urls
        json_data = ('{"due_date": "'+ due_date +'","request_id": {"value": ""}}') #JSON portfolio object
        headers = CaseInsensitiveDict() #Used to send JSON portfolio object.
        headers["Content-Type"] = "application/json" #Used to send JSON portfolio object.
    
        #Variables used to detect and report errors.
        url_error = '<errorsExist>true</errorsExist>' #Test to indicate when an error is pressent in API request url.
        error_message = '<errorMessage>(.+)</errorMessage>' #Extracting the error message from API response.
        data_object_error = '"errorsExist":true' #Test to indicate when an error is pressent in JSON data object.

        #Loop iterating over the number of records in the identifier list. 
        for i in range(len(identifier_list)):
            #Setting the variable for the primary_ID and loan_ID to be used in buidling the url.
            #All variables are converted to string so that the URL can be concatenated.
            primary_ID = str(identifier_list[i])
            loan_ID = str(loan_ID_list[i])
            #Building URL with variables and  API key.
            url = ("https://api-eu.hosted.exlibrisgroup.com/almaws/v1/users/"+ primary_ID +"/loans/" + 
                   loan_ID + "?apikey=" + api_key)
            #Send request using Put URL and data object to Alma. Reponse will be contained in the variable.
            api_response = req.put(url, headers=headers, data=json_data)
    
            #Selection statement if there is an error, add error message to notes column of data frame,
            #else No errors detected.
            #Testing for API url error, if error pressent add error to notes column.
            if url_error in api_response.text:
                note = re.search(error_message, api_response.text)
                df.at[i, 'Note'] = note.group(1)
    
            #Testing for data object error, if error pressent add error to notes column.
            elif data_object_error in api_response.text:
                note = api_response.text
                df.at[i, 'Note'] = note
    
            #Else no errors, add "No errors detected" to notes column.    
            else:
                note = 'No errors detected'
                df.at[i, 'Note'] = note
    
        #save data frame to csv file.
        df.to_csv('bulk_renew_response.csv')
    
        #Print information on number of records and the file name they have been saved to.
        print(str(i + 1) + ' records processed and added to  bulk_renew_response.csv, please check there for details.')






