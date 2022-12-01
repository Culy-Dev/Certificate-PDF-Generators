"""Main module to generate cert url, LinkedIn Badge URL, and subtract 2 business days from session date for an assignment due date"""

import json

from datetime import date, datetime
from calendar import timegm

from hubapi import search_records, UpdateRecordsHandler
from logger import get_logger

from panda_linkedin_urls import PandaLinkedIn
from due_date import DueDate

from models import SQLITE_DB

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

class LinkedInBadgeDueDate:

    def __init__(self, isodate=datetime.date.today()):
        """
        Main class module to run the integration of the certificate information and assignemnt
        due date
        """
        self.engine, self.session = self.get_session()
        # Internal id of the object on hubspot
        self.instance_obj = '2-8311962'
        # Search payload to find records on Hubspot with student who have finished the course,
        # completed the survey, but does not have LinkedIn Badge URL associated with the record.
        self._payload_search_hs = {
            "filterGroups": [
                {
                "filters": [
                    {
                    "value": 'true',
                    "propertyName": "certificate_checkbox",
                    "operator": "EQ"
                    },
                    {
                    "propertyName": "linkedin_badge",
                    "operator": "NOT_HAS_PROPERTY"
                    },
                    {
                    "value": 'true',
                    "propertyName": "survey_completed",
                    "operator": "EQ"
                    }
                ]
                }
            ],
            # Return these properties
            "properties": [
                "hs_object_id",
                "firstname",
                "lastname",
                "course_name", 
                "linkedin_company_id",
                "cle",
                "cle_state_bar_number__and_state__if_not_specified_above_"
            ],
            "limit": 100,
            "after": 0
        } 
        self.isodate = isodate
        midnight=datetime.datetime.combine(self.isodate, datetime.datetime.min.time())
        # Current date at midnight in unix epoch
        self.hs_date=timegm(midnight.timetuple()) * 1000
        # Instantiate the logger
        self.logger = get_logger('LinkedInAssignDueDateUpdate')
        # Payload to update all record with cert urls, LinkedIn Badge url, and assignment_due_date
        self.update_payload_hs = {'inputs': []}
        # Change the object here during projection

    def run(self):
        self._linkedinbadge()
        self._assign_date()

    def get_session(self):
        """Creates a new database self.session for instant use"""

        engine = create_engine(SQLITE_DB )
        session_factory = sessionmaker(bind = engine)
        session = scoped_session(session_factory)
        return (engine, session)

    def _linkedinbadge(self):
        """Main method to gather the cert urls and Linkedin Badge url and update on Hubspot"""
        self.logger.info(f'--- BEGIN LINKEDIN CERTIFICATIONS CREATION ({self.isodate}) ---\n')

        badge = LinkedInBadgeDueDate()

        self.logger.info('Retrieving data from Hubspot...')
        instances_json = search_records(self.instance_obj, self._payload_search_hs).json()
        self.logger.info(f'... Obtained {len(instances_json["results"])} instances to create certifications for.\n')

        self.logger.info(f'Creating Certifications and LinkedIn URL\n')
        for instance in instances_json["results"]:
            try:
                record = PandaLinkedIn(instance, self.isodate, self.engine, self.session)
                record.gather_urls()
                self.update_payload_hs['inputs'].append({'id': instance['id'], 
                                                        'properties': record.urls | {'certificate_issue_year': int(self.isodate.year), 
                                                                                    'certificate_issue_month': int(self.isodate.month),
                                                                                    'certificate_issue_date': self.hs_date}})
            except SQLAlchemyError as s:
                self.logger.error(s, exc_info=True)
                continue
            except Exception as e:
                self.logger.error(e, exc_info=True)
                continue
        self.logger.info(f'\nUrls for {len(self.update_payload_hs["inputs"])} instance(s) have been created.\n')

        add_linkedin_badge = UpdateRecordsHandler('2-7353817')
        add_linkedin_badge.dispatch(self.update_payload_hs)

        self.session.close()
        self.engine.dispose()

        self.logger.info(f'\n--- END LINKEDIN CERTIFICATIONS CREATION ---\n')

    def _assign_date(self):
        """Main method to gather the assignment due date and update on Hubspot"""
        self.logger.info(f'\n--- BEGIN ASSIGNMENTMENT DUE DATE CALCULATION ---\n')

        
        get_appropriate_records = DueDate()
        get_appropriate_records.calc_assign_due_date()
        add_assign_due_date = UpdateRecordsHandler('2-7353817')
        add_assign_due_date.dispatch(get_appropriate_records.payload)
        try:
            self.logger.info(f'\n{len(get_appropriate_records.payload["inputs"])} due date(s) have been added.\n')
        except Exception as e:
            self.logger.error(e, exc_info=True)

        self.logger.info(f'\n--- END ASSIGNMENTMENT DUE DATE CALCULATION ({self.isodate}) ---')

if __name__ == '__main__':
    daily_run = LinkedInBadgeDueDate()
    daily_run.run()
