"""
Command to integrate 3rd party (non-Khan Academy) content
into the topic tree and content directory. 
"""

import glob
import json
import os 
import shutil
from functools import partial
from optparse import make_option
from slugify import slugify

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import settings
from kalite.utils.general import ensure_dir, get_kind_by_extension, humanize_name
from kalite.shared.topic_tools import get_topic_by_path, topics_file, get_topic_tree, get_all_leaves, get_path2node_map
from settings import LOG as logging, LOCAL_CONTENT_ROOT, LOCAL_CONTENT_DATA_PATH


class Command(BaseCommand):
    help = "Inegrate 3rd party content into KA Lite.\nUSAGE:\n  combine -l, -f to map and copy content into the system.\n use -d and -f to remove local content"

    option_list = BaseCommand.option_list + (
        make_option('-l', '--directory-location', action='store', dest='location', default=None,
                    help='The full path of the base directory that contains the 3rd party content.'),
        make_option('-b', '--topic-path', action='store', dest='base_path', default=None,
                    help='Where this content should be inserted into the topic tree.'),
        make_option('-f', '--file-name', action='store', dest='file_name', default=None,
                    help='The name of the file to write as a sibling to topics.json'),
        make_option('-d', '--delete-local-content', action='store_true', dest='flush_content', default=None,
                    help='For testing, delete the local_content directory first, before executing other commands.'),
        make_option('-R', '--restore', action='store_true', dest='restore', default=None,
                    help='For testing, restore topics.json to it\'s original state.'),
    )

    def handle(self, *args, **options):
        if options.get("restore"):
            restore()
        location = options.get("location")
        # append trailing slash to base_path if it's not there
        base_path = options.get("base_path") if options.get("base_path")[-1] == "/" else options.get("base_path") + "/"
        print base_path
        file_name = options.get("file_name")
        flush_content = options.get("flush_content")

    
        # Either we want to add content
        if location and base_path and file_name and not flush_content:
            # Location must be valid
            if not os.path.exists(location):
                raise CommandError("The location given:'%s' does not exist on your computer. \
                    Please enter a valid directory." % location)
            # Base path must be valid
            if not get_topic_by_path(base_path):
                raise CommandError("The base path:'%s' does not exist in topics.json. \
                    Please enter a valid base path." % base_path)
            # File name must be unique
            if os.path.exists(os.path.join(settings.DATA_PATH, file_name)):
                raise CommandError("The file name '%s' is taken. \
                    Please specify a unique file name." % file_name)

            add_content(location, base_path, file_name)
            logging.info("Successfully added content bundle %s" % file_name)

        # Or remove content
        elif flush_content and file_name and not (location and base_path):
            # File name must exist
            if not os.path.exists(os.path.join(settings.DATA_PATH, file_name)):
                raise CommandError("The file name '%s' does not exist. \
                    Please specify a valid file name." % file_name)

            remove_content(file_name)
            logging.info("Successfully removed content bundle %s" % file_name)

        # Nothing else can happen
        else:
            raise CommandError("Must specify a combination of -l, -b, and -f \
                to add content OR -d and -f to remove content.")
    

def add_content(location, base_path, file_name):
    """
    Take a "root" location and add content to system by mapping file 
    hierarchy to JSON, copying content into the local_content directory, 
    and updating the topic tree with the mapping inserted. 
    """

    def get_children(location, base_path):
        """Return list of dictionaries of subdirectories and/or files in the location"""
        # Recursively add all subdirectories
        children = []

        subdirectories = [os.path.join(location, s) for s in os.listdir(location) if os.path.isdir(os.path.join(location, s))]
        for dirpath in subdirectories:
            base_name = os.path.basename(dirpath)
            topic_slug = slugify(base_name)
            current_path = os.path.join(base_path, topic_slug)
            children.append({
                "kind": "Topic",
                "path": current_path, 
                "id": topic_slug, 
                "title": humanize_name(base_name), 
                "slug": topic_slug,
                "description": "",
                "parent_id": os.path.basename(base_path),
                "ancestor_ids": filter(None, base_path.split("/")),
                "contains": recurse_container(dirpath),
                "hide": False, 
                "children": get_children(dirpath, current_path), 
            })

        # Add all files
        files = [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))]
        for filepath in files:
            full_filename = os.path.basename(filepath)
            kind = get_kind_by_extension(full_filename)
            if kind is not "Video":
                continue

            filename = os.path.splitext(full_filename)[0]
            extension = os.path.splitext(full_filename)[1].lower()
            file_slug = slugify(filename)
            children.append({
                "youtube_id": file_slug, 
                "id": file_slug,
                "title": humanize_name(filename),
                "path": os.path.join(base_path, file_slug),
                "ancestor_ids": filter(None, base_path.split("/")),
                "slug": file_slug,
                "parent_id": os.path.basename(base_path),
                "kind": kind,
            })

            # Copy over content
            ensure_dir(LOCAL_CONTENT_ROOT)
            normalized_filename = "%s%s" % (file_slug, extension)
            # shutil.copy(filepath, os.path.join(LOCAL_CONTENT_ROOT, normalized_filename))
            logging.info("Copied file %s to local \
                content directory." % os.path.basename(filepath))
        return children  

    def recurse_container(location):
        """Return list of kinds of containers beneath this location in the file hierarchy"""
        contains = set()
        if [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))]:
            contains.add("Video") # TODO(dylan) assuming video here

        subdirectories = [os.path.join(location, s) for s in os.listdir(location) if os.path.isdir(os.path.join(location, s))]
        for dirpath in subdirectories:
            contains.add("Topic")
            contains.update(recurse_container(dirpath))
        return list(contains)

    # Generate topic_tree from file hierarchy
    nodes = get_children(location, base_path)

    # Write it to JSON
    ensure_dir(settings.LOCAL_CONTENT_DATA_PATH)
    write_location = os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name)
    with open(write_location, "w") as dumpsite:
        json.dump(nodes, dumpsite, indent=4)
    logging.info("Wrote output to %s" % write_location)

    # Update topic tree with desired mapping
    inject_topic_tree(nodes, base_path)


def inject_topic_tree(local_content, base_path):
    """Insert all local content into topic_tree"""
    topic_file_path = os.path.join(settings.DATA_PATH, topics_file)
    topic_tree = get_topic_tree()

    get_path2node_map()

    with open(topic_file_path, 'w') as f:
        json.dump(topic_tree, f)
    logging.info("Rewrote topic tree: %s" % topic_file_path)


# def remove_content(file_name):
#     """
#     Remove content from the system by deleting the mapping,
#     deleting any content contained in the mapping from the content
#     directory, and restoring the topic_tree to it's former glory.
#     """
#     if not os.path.exists(settings.LOCAL_CONTENT_DATA_PATH, file_name):
#         raise CommandError("Invalid name for local_content. File must exist inside ka-lite/data/local_content/")
#     with open(os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name)) as f:
#         local_content = json.load(f)
    
#     def restore_topic_tree(local_content):
#         """Remove local_content from topics.json"""
#         topic_tree = get_topic_tree()
#         ## TODO topic_tree.deepsubtract(local_content)
#         with open(os.path.join(settings.DATA_PATH, topics_file), 'w') as f:
#             json.dump(topic_tree, f)

#     restore_topic_tree(local_content)

#     # Second, delete local content based on mapping
#     def delete_local_content(local_content):
#         """Remove local content videos from content directory"""
#         videos = get_all_leaves(local_content, "Video")
#         for v in videos:

    # Finally delete the mapping


def restore():
    os.remove(os.path.join(settings.DATA_PATH, "topics.json"))
    shutil.copy2(os.path.join(settings.DATA_PATH, "permtopics.json"), os.path.join(settings.DATA_PATH, "topics.json"))
