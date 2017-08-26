"""
-------------------------------------------------------------
                    HELPER FUNCTIONS
Some useful tools to be re-used throughout the program.
-------------------------------------------------------------

"""

from flask import session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import models
from random import SystemRandom



def get_user():

    """Returns the User record associated with the active session. 
       Retuns None if no active session is found.
    """
    if not 'username' in session:
        return None
    username = session['username'].lower()
    return models.User.query.filter(func.lower(models.User.username) == username).first()
    

def valid_username(username):

    # username: str
    # return: bool
    
    return username.isalnum() and len(username) <= 20


def valid_file(filename):
    
    # filename: str
    # return: bool

    """Validates a file extension by checking it against a 
       whitelist of allowed types.
    """

    allowed = set(["exe", "jpg", "png", "gif", "bmp", "jpeg", "webm", 
                   "wmv", "avi", "mov", "rar", "sai", "tar", "zip", "psd", 
                   "xm", "mp3", "wav", "mod", "bmp", "tiff", "txt", "it", 
                   "rb", "ogg", "mpg", "mpeg", "sid", "php", "py","7z","pub"])
                  
    return filename.split('.')[-1].lower() in allowed



def generate_random_string(length):

    # length: int
    # return: str
    
    """Generates cryptographically random base-64 string.
    """
    number_generator = SystemRandom()
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    id = ""
    for i in range(length):
        id += chars[ number_generator.randrange(len(chars)) ]
    return id
    

            
def format_bytes(num):
    """Returns the filesize as a string.
       e.g. '400 MB', '250 KB', etc.
    """
    # return: str
    if num >= 10**9:
        return str(round(float(num) / 10**9, 1)) + " GB"
    if num >= 10**6:
        return str(round(float(num) / 10**6, 1)) + " MB"
    if num >= 10**3:
        return str(num / 10**3) + " KB"
    return str(num) + " B"
