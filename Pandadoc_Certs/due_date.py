"""Module to subtract 2 business days from a class's session date to give a assignment due date."""

import logging
import pandas as pd
from pandas.tseries.offsets import BDay
from hubapi import get_all_records
from dateutil.parser import parse
from calendar import timegm
import datetime

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

class DueDate:
    def __init__(self, objectType='2-8311962', curr_date=datetime.date.today()):
        """A class to generate the payload to update assignment due date."""
        # Get all the records of an object with specified properties
        self.records = self.get_all_records_with_property(objectType)
        self.curr_date = datetime.datetime.combine(curr_date, datetime.datetime.min.time()).replace(tzinfo=datetime.timezone.utc)
        # Update payload for the records
        self.payload = {'inputs': []}
    
    def calc_assign_due_date(self):
        """
        Takes the records live_session_date and subtracts 2 business days. Subtracts 2 business
        days and makes the assignment_due_date. Input the information in a payload.
        """
        for row in self.records.itertuples(index=True, name="Pandas"):
            try:
                # row[-1] is pulling from properties.live_session_datetime
                live_session_date = datetime.datetime.fromisoformat(row[-1][:-1]).replace(tzinfo=datetime.timezone.utc) 
                if self.curr_date < live_session_date: 
                    assignment_due_date = live_session_date - BDay(2)
                    assignment_due_date_unix = timegm(assignment_due_date.timetuple()) * 1000
                    self.payload['inputs'].append({'id': row.id, 'properties': {"assignment_due_date": assignment_due_date_unix}})
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
    
    def get_all_records_with_property(self, objectType, property_name={'live_session_datetime', 'assignment_due_date'}):
        """Take JSON data from a GET request and generate a dataframe. Extract only the records 
        that have a live_session_date but no assignment_due_date
        Args:
            objectType (str): Internal name of the object to do a GET request
            property_name (dict, optional): a dictionary to pass as a parameter to the GET request
                to only pull in the properties in the dictionary. Defaults to 
                {'live_session_datetime', 'assignment_due_date'}.
        Returns:
            pandas dataframe: A pandas dataframe of only the records that have a live_session_date 
                but no assignment_due_date
        """
        all_records = get_all_records(objectType, add_params={'properties': property_name})
        records_in_hs = pd.json_normalize(all_records)
        records_in_hs = records_in_hs[(records_in_hs['properties.live_session_datetime'].notnull()) & ((records_in_hs['properties.assignment_due_date'].isnull()) | (records_in_hs['properties.assignment_due_date']==''))]
        return records_in_hs