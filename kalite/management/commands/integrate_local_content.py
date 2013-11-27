"""
Command to integrate 3rd party (non-Khan Academy) content
into the topic tree and content directory
"""

import glob
import json
import os 
import shutil
from optparse import make_option
from slugify import slugify

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from kalite.utils.general import ensure_dir, path_leaf, get_file_type_by_extension, slugify_path
from kalite.shared.topic_tools import get_topic_by_path
from settings import LOG as logging, LOCAL_CONTENT_ROOT


class Command(BaseCommand):
    help = "Inegrate 3rd party content into KA Lite"
    option_list = BaseCommand.option_list + (
        make_option('-l', '--directory-location', action='store', dest='location', default=None,
                    help='The full path of the base directory that contains the 3rd party content.'),
        make_option('-b', '--topic-path', action='store', dest='base_path', default=None,
                    help='Where this content should be inserted into the topic tree.'),
        make_option('-f', '--file-name', action='store', dest='file_name', default=None,
                    help='The name of the file to write as a sibling to topics.json'),
        make_option('-C', '--copy-content', action='store_true', dest='copy_content', default=None,
                    help='Copy any files found into the content/local_content/ directory so that \
                    they can be found by the system'),
        make_option('-D', '--flush-local-content', action='store_true', dest='flush_content', default=None,
                    help='For testing, delete the local_content directory first, \
                    before executing other commands.'),
    )

    def handle(self, *args, **options):
        # delete local_content if flag given
        if options.get("flush_content") and os.path.exists(LOCAL_CONTENT_ROOT):
            logging.info("Removing local content directory.") 
            shutil.rmtree(LOCAL_CONTENT_ROOT)

        logging.info("Verifying that all arguments are valid.")
        location, base_path, file_name, copy_content = verify_options(**options)

        logging.info("Mapping file hierarchy to JSON")
        map_file_hierarchy(location, base_path, copy_content, file_name)


def verify_options(**options):
    """Verify that arguments passed exist and are valid. Returns tuple."""
    # pull out options
    location = options.get("location")
    base_path = options.get("base_path")
    file_name = options.get("file_name")
    copy_content = options.get("copy_content")

    if not location:
        raise CommandError("Must specify --directory-location (-l)")
    elif not base_path:
        raise CommandError("Must specify --topic-path (-b)")
    elif not file_name:
        raise CommandError("Must specify --file-name (-f)")
    
    # Location must be valid
    if not os.path.exists(location):
        raise CommandError("The location given:'%s' does not exist on your computer. \
        Please enter a valid directory." % location)

    # Base path must be valid
    if not get_topic_by_path(base_path):
        raise CommandError("The base path:'%s' does not exist in topics.json. \
        Please enter a valid base path. (Hint: don't forget the closing slash! e.g. /math/" % base_path)

    # File name must be unique
    if os.path.exists(os.path.join(settings.DATA_PATH, file_name)):
        raise CommandError("The file name '%s' is taken. Please specify a unique file name." % file_name)

    return location, base_path, file_name, copy_content

def map_file_hierarchy(location, base_path, copy_content, file_name):
    """Traverse the directory location and generate JSON hierarchy from it"""
    
    # Create base entry
    master_blob = {
        "id": "master",
        "path": base_path,
        "children": get_children(location, base_path, copy_content),
    }

    ensure_dir(settings.EXTRA_TOPICS_PATH)
    write_location = os.path.join(settings.EXTRA_TOPICS_PATH, file_name)
    with open(write_location, "w") as dumpsite:
        logging.info("Writing output to %s" % write_location)
        json.dump(master_blob, dumpsite, indent=4)


def get_children(location, base_path, copy_content):
    """Return list of dictionaries of subdirectories and/or files in the location"""
    # Recursively add all subdirectories
    children = []
    slugified_base_path = slugify_path(base_path)
    for dirpath in glob.glob(os.path.join(location, "*/")):
        dirname = path_leaf(dirpath)
        topic_slug = slugify(dirname)
        current_path = os.path.join(slugified_base_path, topic_slug)
        children.append({
            "kind": "Topic",
            "path": current_path, 
            "id": topic_slug, 
            "title": dirname, 
            "slug": topic_slug,
            "node_slug": topic_slug,
            "parent_id": os.path.basename(slugified_base_path),
            "ancestor_ids": filter(None, slugified_base_path.split("/")),
            "topic_page_url": current_path, 
            "extended_slug": current_path.strip("/"),
            "hide": False, 
            "children": get_children(dirpath, current_path, copy_content), 
        })

    # Add all files
    for filepath in glob.glob(os.path.join(location, "*.*")):
        full_filename = os.path.basename(filepath)
        file_type = get_file_type_by_extension(full_filename)
        if not file_type:
            raise CommandError("Can't tell what type of file this is by the extension \
                    '%s'. Please add to lookup dictionary and re-run command." % full_filename)
        
        filename = os.path.splitext(full_filename)[0]
        extension = os.path.splitext(full_filename)[1].lower()
        file_slug = slugify(filename)
        children.append({
            "youtube_id": file_slug, 
            "id": file_slug,
            "title": filename,
            "path": os.path.join(slugified_base_path, file_slug),
            "ancestor_ids": filter(None, slugified_base_path.split("/")),
            "slug": file_slug,
            "parent_id": os.path.basename(slugified_base_path),
            "kind": file_type,
        })

        if copy_content:
            ensure_dir(LOCAL_CONTENT_ROOT)
            normalized_filename = "%s%s" % (file_slug, extension)
            shutil.copy(filepath, os.path.join(LOCAL_CONTENT_ROOT, normalized_filename))
            logging.info("Copied file %s to local content directory." % os.path.basename(filepath))
    return children  