"""
Using the template provided by the pdfgeneratorapi team, we input student course information
to generate a certificate. A LinkedIn URL is later created to add the certificate directly 
to the student's LinkedIn account when clicked.
"""

import requests
import os
import logging
import json
import time

from urllib.parse import urlencode
from dotenv import load_dotenv

from sqlalchemy import insert, desc, create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

from models import CertIdHistory, SQLITE_DB 
from aws_bucket import transfer_cert_to_aws

import pdf_generator_api_client

from pdf_generator_api_client.api import documents_api
from pdf_generator_api_client.model.batch_data import BatchData
from pdf_generator_api_client.model.inline_response2004 import InlineResponse2004
from pdf_generator_api_client.model.inline_response401 import InlineResponse401
from pdf_generator_api_client.model.inline_response402 import InlineResponse402
from pdf_generator_api_client.model.inline_response403 import InlineResponse403
from pdf_generator_api_client.model.inline_response404 import InlineResponse404
from pdf_generator_api_client.model.inline_response422 import InlineResponse422
from pdf_generator_api_client.model.inline_response500 import InlineResponse500

load_dotenv()

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

PDFGENAPI_JWT = os.environ['PDFGENAPI_JWT']

configuration = pdf_generator_api_client.Configuration(
    host = "https://us1.pdfgeneratorapi.com/api/v4"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): JSONWebTokenAuth
configuration = pdf_generator_api_client.Configuration(
    access_token = PDFGENAPI_JWT
)

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


class PdfGenAPILinkedIn:
    def __init__(self, hs_record, date, engine=None, session=None):
        """
        Class to generate a certificate from student course data, gather the urls of 2 certificates
        and the url to add the certificate to the student's LinkedIn account.
        """
        self.urls = {} # Dict to hold 2 cert urls and linkedin url
        self.engine = engine
        self.session = session
        # Information pulled from hubspot to be added to the certificates
        self.firstname = hs_record['properties']['firstname']
        self.lastname = hs_record['properties']['lastname']
        self.course_name = hs_record['properties']['course_name']
        self.linkedin_company_id = hs_record['properties']['linkedin_company_id']
        self.hs_obj_id = hs_record['properties']['hs_object_id']
        self.cle = hs_record['properties']['cle']
        self.cle_state_bar_num = hs_record['properties']['cle_state_bar_number__and_state__if_not_specified_above_']
        self.date = date
        
        self.template_id_compl_cert = 477969 # Template 1 PDFGeneratorAPI ID
        # Body to house information to be added to Template 1
        self.body_completion_cert = {"stu fname stu lname": f"{self.firstname} {self.lastname}",
                "course name": self.course_name,
                "date issued": self.date
            }
        self.name_compl_cert = f"{self.course_name} - {self.firstname} {self.lastname} Certificate - LinkedIn Ref"
        
        self.template_id_cle_cert = 468378 # Template 2 PDFGenerator API ID
        # Body to house information to be added to Template 2
        self.body_cle_cert = {"stu fname stu lname": f"{self.firstname} {self.lastname}",
                "course name": self.course_name,
                "date issued": self.date,
                "cle credits": self.cle,
                "cle state bar number": self.cle_state_bar_num
            }
        self.name_cle_cert = f"{self.course_name} - {self.firstname} {self.lastname} Certificate - CLE INFO"

    def create_cert_id(self):
        """Each time a certificate is created, generate and ID that will be added to a SQLite
        Table for historical purposes

        Returns:
            cert_id (str): The unique id of the certificate in nnn-nnnnn-nn format
        """
        stmt = CertIdHistory(hs_instance_id=self.hs_obj_id)
        self.session.add(stmt)
        self.session.commit()
        # Get the last id created, and fill in leading 0s so that the number is 10 digits total
        cert_id_query = str(self.session.query(CertIdHistory.cert_id).filter_by(hs_instance_id=self.hs_obj_id).first()[0]).zfill(10)
        cert_id = f'{cert_id_query[:3]}-{cert_id_query[3:8]}-{cert_id_query[8:]}' 
        return cert_id 


    def gather_urls(self):
        """
        Main function to gather the urls of the certs and linkedin badge to be input into 
        the url dictionary
        """
        try:
            base64_compl_cert, name_compl_cert = self.create_cert(self.template_id_compl_cert, self.body_completion_cert, self.name_compl_cert)
            self.urls['linkedin_certificate_url'] = transfer_cert_to_aws(base64_compl_cert, name_compl_cert)
            self.urls['unique_certificate_id'] = self.create_cert_id()
            self.urls['linkedin_badge'] = self.create_linkedin_url(self.urls['linkedin_certificate_url']) 
            
            base64_cle_cert, name_cle_cert = self.create_cert(self.template_id_cle_cert, self.body_cle_cert, self.name_cle_cert)
            self.urls['cle_certificate_url'] = transfer_cert_to_aws(base64_cle_cert, name_cle_cert)
        except Exception as e:
            logger.error(e, exc_info=True)
            pass
        
    def create_cert(self, template_id, body, name):
        """Function to house PDFGeneratorAPI's code to generate a certificate.

        Args:
            template_id (str): Unique ID of the certificate.
            body (dict): a "payload" that houses the student/course information to be added.
            name (str): Name of the certificate in: "course_name - first_name last_name format"

        Returns:
            base64, name(str): the base64 of the cert to be added to AWS and name of cert
        """
    # Enter a context with an instance of the API client
        with pdf_generator_api_client.ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = documents_api.DocumentsApi(api_client)
            body = body # {str: (bool, date, datetime, dict, float, int, list, str, none_type)} | Data used to generate the PDF. This can be JSON encoded string or a public URL to your JSON file.
            name = name # str | Document name, returned in the meta data. (optional)
            format = "pdf" # str | Document format. The zip option will return a ZIP file with PDF files. (optional) (default to "pdf")
            output = "base64" # str | Response format. "I" is used to return the file inline. With the url option, the document is stored for 30 days and automatically deleted. (optional) (default to "base64")

            try:
                # Generate document
                api_response = api_instance.merge_template(template_id, body, name=name, format=format, output=output)
                return api_response['response'], name
            except pdf_generator_api_client.ApiException as e:
                logger.error(e, exc_info=True)
                pass


    def create_linkedin_url(self, merged_doc_url, org_id=12958828):
        """Creates the LinkedIn badge url of the cert. A student can click on the url to add the
        Cert to their LinkedIn profile.

        Args:
            merged_doc_url (str): url of the cert
            org_id (int, optional): Org ID of whoever is providing the cert. 
                Defaults to the client's org id

        Returns:
            final_url (str): Linkedin Badge URL. When a student is signed in LinkedIn and clicks
                on the URL, it will generate the certificate information to add to their profile.
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
