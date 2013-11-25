"""
Command to integrate 3rd party (non-Khan Academy) content
into the topic tree and content directory
"""

import glob
import json
import ntpath
import os 
import shutil
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from kalite.utils.general import ensure_dir 
from kalite.shared.topic_tools import get_topic_by_path
from settings import LOG as logging, LOCAL_CONTENT_ROOT


class Command(BaseCommand):
    help = "Inegrate 3rd party content into KA Lite"
    option_list = BaseCommand.option_list + (
        make_option('-l', '--directory-location', action='store', dest='location', default=None,
                    help='The full path of the base directory that contains the 3rd party content.'),
        make_option('-b', '--topic-path', action='store', dest='base_path', default=None,
                    help='Where this content should be inserted into the topic tree.'),
        make_option('-C', '--copy-content', action='store_true', dest='copy_content', default=None,
                    help='Copy any files found into the content/local_content/ directory so that they can be found by the system'),
        make_option('-D', '--flush-local-content', action='store_true', dest='flush_content', default=None,
                    help='For testing, delete the local_content directory first, before executing other commands.'),
    )

    def handle(self, *args, **options):
        if options.get("flush_content") and os.path.exists(LOCAL_CONTENT_ROOT):
            logging.info("Removing local content directory.") 
            shutil.rmtree(LOCAL_CONTENT_ROOT)
        
        location = options.get("location")
        base_path = options.get("base_path")
        copy_content = options.get("copy_content")
        logging.info("Verifying that all arguments are valid.")
        verify_options(location, base_path)

        logging.info("Mapping file hierarchy to JSON")
        map_file_hierarchy(location, base_path, copy_content)


def verify_options(location, base_path):
    """Verify that arguments passed exist and are valid"""

    if not location or not base_path:
        raise CommandError("Must specify --directory-location (-l) and --topic-path (-b)")
    
    # Location must be valid
    if not os.path.exists(location):
        raise CommandError("The location given:'%s' does not exist on your computer. Please enter a valid directory." % location)

    # Base path must be valid
    if not get_topic_by_path(base_path):
        raise CommandError("The base path:'%s' does not exist in topics.json. Please enter a valid base path. (Hint: don't forget the closing slash! e.g. /math/" % base_path)


def map_file_hierarchy(location, base_path, copy_content):
    """Traverse the directory location and generate JSON hierarchy from it"""
    # Create base entry
    master_blob = {
        "id": "master",
        "path": base_path,
        "children": get_children(location, base_path, copy_content),
    }
    print json.dumps(master_blob, indent=4)
    return master_blob


def get_children(location, base_path, copy_content):
    """Return list of dictionaries of subdirectories and/or files in the location"""
    # Recursively add all subdirectories
    children = []
    for directory in glob.glob(os.path.join(location, "*/")):
        current_path = os.path.join(base_path, path_leaf(directory))
        children.append({
            "path": current_path, 
            "id": path_leaf(directory),  
            "children": get_children(directory, current_path, copy_content), 
        })

    # Add all files
    for filename in glob.glob(os.path.join(location, "*.*")):
        children.append({
            "id": path_leaf(filename),
            "path": os.path.join(base_path, path_leaf(filename)),
            "parent_id": path_leaf(path=base_path),
            "type": "video",
        })

        if copy_content:
            ensure_dir(LOCAL_CONTENT_ROOT)
            shutil.copy(filename, LOCAL_CONTENT_ROOT)
            logging.info("Copied file %s to local content directory." % path_leaf(filename))

    return children


# Thanks: http://stackoverflow.com/a/8384788
def path_leaf(path, head=True):
    """Return the name of the current directory of the filepath, or the parent"""
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)