"""
Using the template provided by the pandadocs], we input student course information
to generate a certificate. A LinkedIn URL is later created to add the certificate directly 
to the student's LinkedIn account when clicked.
"""

import requests
import os
import logging
import json
import time

from urllib.parse import quote, urlencode
from dotenv import load_dotenv

from sqlalchemy import insert, desc, create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

from models import CertIdHistory, SQLITE_DB 

load_dotenv()

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

PANDA_API = os.environ['PANDA_API']
TEMPLATE_ID = os.environ['TEMPLATE_ID'] # Pandadoc template ID
FOLDER_ID = os.environ['FOLDER_ID'] # Location in Pandadocs to put templates

headers = {'Authorization': f'API-Key {PANDA_API}', 'Content-Type': 'application/json'}

def api_log(res, success_code):
    if res.status_code == success_code:
        logger.debug(F'"METHOD": "{res.request.method}", '
                    F'"STATUS_CODE": "{res.status_code}",'
                    F'"URL": "{res.url}"', exc_info=True)
        return res
    else:
        logger.warning(F'"METHOD": "{res.request.method}", '
                       F'"STATUS_CODE": "{res.status_code}",'
                       F'"URL": "{res.url}",'
                       F'"FAIL RESPONSE": "{res.text}"', exc_info=True)
        return None


class PandaLinkedIn:
    def __init__(self, hs_record, date, engine=None, session=None):
        """
        Class to generate a certificate from student course data, gather the urls of the AWS pdf certificates
        and the url to add the certificate to the student's LinkedIn account.
        """
        self.urls = {} # Dict to holdcert urls and linkedin url
        self.engine = engine
        self.session = session
        # Information pulled from hubspot to be added to the certificates
        self.firstname = hs_record['properties']['firstname']
        self.lastname = hs_record['properties']['lastname']
        self.course_name = hs_record['properties']['course_name']
        self.linkedin_company_id = hs_record['properties']['linkedin_company_id']
        self.email = hs_record['properties']['email']
        self.cert_id = self.create_cert_id(hs_record['properties']['hs_object_id'])
        self.date = date

    def create_cert_id(self, hs_obj_id):
        """Each time a certificate is created, generate and ID that will be added to a SQLite
        Table for historical purposes

        Args:
            hs_obj_id (int): Hubspot ID to store with unique cert id historical data

        Returns:
            cert_id(str): The unique id of the certificate in nnn-nnnnn-nn format
        """
        stmt = CertIdHistory(hs_instance_id=hs_obj_id)
        self.session.add(stmt)
        self.session.commit()
        # Get the last id created, and fill in leading 0s so that the number is 10 digits total
        cert_id_query = str(self.session.query(CertIdHistory.cert_id).filter_by(hs_instance_id=hs_obj_id).first()[0]).zfill(10)
        cert_id = f'{cert_id_query[:3]}-{cert_id_query[3:8]}-{cert_id_query[8:]}'
        self.urls['unique_certificate_id'] = cert_id 
        return cert_id 


    def gather_urls(self):
        """
        Main function to gather the urls of the certs and linkedin badge to be input into 
        the url dictionary
        """
        doc_id = self.create_pd_cert().json()['id']
        time.sleep(5) # Takes 3-5 seconds to change from document.uploaded to document.draft - https://developers.pandadoc.com/reference/new-document
        self.update_doc_status(doc_id) # Must change to document.completed to further modify
        cert_id = self.create_cert_url(doc_id).json()['id']
        cert_url = f'https://app.pandadoc.com/s/{cert_id}' # Create the url to the cert
        
        # Store the cert url and LinkedIn Badge url in order to upload in HS via a payload
        self.urls['certificate_file_url'] = cert_url
        self.urls['linkedin_badge'] = self.create_linkedin_url(cert_url)


    def create_pd_cert(self):
        """Creates certificates from Pandadoc Templates

        Returns:
            res: API response for certificate generation
        """
        # template ID logic; if "generate" field known and is true, push corresponding PD template ID and timestamp to dict
        url = "https://api.pandadoc.com/public/v1/documents"
        payload = {
            "name": f"{self.course_name} - {self.firstname} {self.lastname} Certificate",
            "template_uuid": TEMPLATE_ID,
            "folder_uuid": FOLDER_ID ,
            "recipients": [{"email": self.email}],
            "tokens": [
                {"name": "Student FName Student LName", "value": f"{self.firstname} {self.lastname}"},
                {"name": "Course Name", "value": self.course_name},
                {"name": "Date Issued", "value": str(self.date)}
            ]
        }

        res = requests.post(url, headers=headers, data=json.dumps(payload))

        return api_log(res, 201)

    def update_doc_status(self, doc_id):
        """Change to document.completed in order to actually further process the cert"""
        url = f"https://api.pandadoc.com/public/v1/documents/{doc_id}/status/"

        payload = {
            "status": 2 # code for document.completed
        }

        res = requests.patch(url, headers=headers, data=json.dumps(payload))

        return api_log(res, 204)

    def create_cert_url(self, doc_id):
        """Creates the certificate URL from the cert document id

        Args:
            doc_id : unique cert id to be input in url

        Returns:
            res: API JSON response
        """
        url = f"https://api.pandadoc.com/public/v1/documents/{doc_id}/session"

        payload = {
            'silent': 'true',
            "recipient": self.email
        }

        res= requests.post(url, data=json.dumps(payload), headers=headers)

        return api_log(res, 201)

    def create_linkedin_url(self, merged_doc_url, org_id):
        """Creates the LinkedIn badge url of the cert. A student can click on the url to add the
        Cert to their LinkedIn profile.

        Args:
            merged_doc_url (str): url of the cert
            org_id (int, optional): Org ID of whoever is providing the cert. 
                Defaults to the client's org id

        Returns:
            final_url (str): Linkedin Badge URL
        """
        base_url = "https://www.linkedin.com/profile/add?"
        params= {
            'startTask': 'CERTIFICATION_NAME',
            'name': "Certificate of Completion: " + self.course_name,
            'organizationId': org_id,
            'issueYear': self.date.year,
            'issueMonth': self.date.month,
            'certUrl': merged_doc_url,
            'certId': self.urls['unique_certificate_id']
        }
        final_url = base_url + urlencode(params)

        return final_url
