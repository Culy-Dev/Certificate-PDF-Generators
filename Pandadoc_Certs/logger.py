"""Module to create set logging levels and handlers"""

import logging
import sys

import os # Delete later

import datetime

# Custom formatter
class MyFormatter(logging.Formatter):
    """A Class to using inheritance to create a custom formatter"""
    dbg_fmt = '{asctime} | {levelname}\n' \
               '    [{name}:{lineno:3}] {message}'
    wrn_fmt = '{asctime} | {levelname}\n' \
              '{{\n' \
              '"loggername" : "{name}",\n' \
              '"filename": "{filename}",\n' \
              '"funcName": "{funcName}",\n' \
              '"lineno": "{lineno}",\n' \
              '"module": "{module}",\n' \
              '"pathname": "{pathname},"\n' \
              '"message": {{{message}}}\n' \
              '}}'

    dt_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super().__init__(fmt="{levelname} {msg}", datefmt=self.dt_format, style='{')

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            self._style._fmt = MyFormatter.dbg_fmt

        elif record.levelno == logging.INFO:
            self._style._fmt = MyFormatter.dbg_fmt

        elif record.levelno == logging.ERROR:
            self._style._fmt = MyFormatter.wrn_fmt

        elif record.levelno == logging.WARNING:
            self._style._fmt = MyFormatter.wrn_fmt
        
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = MyFormatter.wrn_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result

def get_file_handler():
    """
    Sets the lowest logging level of the file_handler to DEBUG and format the log message to 
    the custom MyFormatter 
    Returns:
        file_handler (class): sends logging output to a disk file
    """
    isodatetime=datetime.datetime.utcnow().isoformat()
    curr_dir = os.getcwd()
    log_fname = os.path.join(os.path.dirname(__file__) + os.sep, 'log',F'{isodatetime}_LinkedInUpdate.log' )
    file_handler = logging.FileHandler(log_fname, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(MyFormatter())
    return file_handler

def get_console_handler():
    """
    Sets the lowest logging level of the file_handler to DEBUG and format the log message to 
    the custom MyFormatter 
    Returns:
        console_handler (class): sends logging output to the sys.stdout stream
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(MyFormatter())
    return console_handler

def get_syslog_handler():
    """
    Sets the lowest logging level of the file_handler to DEBUG and format the log message to 
    the custom MyFormatter 
    
    Returns:
        external_handler (class): sending logging messages to papertrail cloud hosting management
        system
    """
    external_handler = SysLogHandler(address=(paper_trail_address, port))
    external_handler.setLevel(logging.DEBUG)
    external_handler.setFormatter(MyFormatter())
    return external_handler

def get_logger(logger_name):
    """
    Set a logger with 3 handlers from the 3 helper functions above
    Args:
        logger_name (str): name of the logger to be used
    Returns:
        logger (class): root logger in the hierachy
    """
    # Set the logger
    logger = logging.getLogger(logger_name) 
    logger.setLevel(logging.DEBUG) # better to have too much log than not enough

    if not logger.handlers:
        logger.addHandler(get_file_handler()) # Get rid of later
        logger.addHandler(get_console_handler())
        # logger.addHandler(get_syslog_handler()) # add later

    return logger
