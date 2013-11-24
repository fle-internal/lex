"""
Command to integrate 3rd party (non-Khan Academy) content
into the topic tree and content directory
"""

import glob
import ntpath
import os 
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from kalite.shared.topic_tools import get_topic_by_path
from settings import LOG as logging


class Command(BaseCommand):
    help = "Inegrate 3rd party content into KA Lite"
    option_list = BaseCommand.option_list + (
        make_option('-l', '--directory-location', action='store', dest='location', default=None,
                    help='The full path of the base directory that contains the 3rd party content.'),
        make_option('-b', '--topic-path', action='store', dest='base_path', default=None,
                    help='Where this content should be inserted into the topic tree.'),
    )

    def handle(self, *args, **options):
        location = options.get("location")
        base_path = options.get("base_path")
        logging.info("Verifying that all arguments are valid.")
        verify_options(location, base_path)

        logging.info("Mapping file hierarchy to JSON")
        topics_blob = map_file_hierarchy(location, base_path)


def verify_options(location, base_path):
    """Verify that arguments passed exist and are valid"""

    if not location or not base_path:
        raise CommandError("Must specify --directory-location (-l) and --topic-path (-b)")
    
    # Location must be valid
    if not os.path.exists(location):
        raise CommandError("The location given:'%s' does not exist on your computer. Please enter a valid directory." % location)

    # Base path must be valid
    if not get_topic_by_path(base_path):
        raise CommandError("The base path:'%s' does not exist in topics.json. Please enter a valid base path.")


def map_file_hierarchy(location, base_path):
    """Traverse the directory location and generate JSON hierarchy from it"""
    # Create base entry
    master_blob = {
        "id": "master",
        "children": get_children(location),
    }
    return master_blob

def get_children(location):
    """Return list of dictionaries of subdirectories and/or files in the location"""
    # Recursively add all subdirectories
    children = []
    for directory in glob.glob(os.path.join(location, "*/")):
        children.append({
                "id": path_leaf(directory),
                "type": "subdirectory",
                "children": get_children(directory), # a list of the subdirectories or movies inside that directory
            })

    # Add all files
    for filename in glob.glob(os.path.join(location, "*.*")):
        children.append({
                "id": path_leaf(filename),
                "type": "video",
            })

    return children


# Thanks: http://stackoverflow.com/a/8384788
def path_leaf(path):
    """Return the name of the current directory of the filepath"""
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)