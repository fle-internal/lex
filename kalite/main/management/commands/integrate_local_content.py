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
from settings import LOG as logging, LOCAL_CONTENT_ROOT, LOCAL_CONTENT_DATA_PATH
from shared.topic_tools import get_topic_by_path, topics_file, get_topic_tree, get_all_leaves, get_path2node_map, get_parent
from utils.general import ensure_dir, get_kind_by_extension, humanize_name


class Command(BaseCommand):
    help = "Inegrate 3rd party content into KA Lite.\nUSAGE:\n  combine -l, -f to map and copy content into the system.\n use -d and -f to remove local content"

    option_list = BaseCommand.option_list + (
        make_option('-l', '--directory-location', action='store', dest='location', default=None,
                    help='The full path of the base directory that contains the 3rd party content.'),
        make_option('-p', '--parent-path', action='store', dest='parent_path', default=None,
                    help='Parent node under which the given directory (topic) should be inserted under'),
        make_option('-c', '--copy', action='store_true', dest='copy', default=None,
                    help='Copy resource files to the content directory'),
        make_option('-m', '--move', action='store_true', dest='move', default=None,
                    help='Move resource files to the content directory'),

        make_option('-d', '--delete-content', action='store_true', dest='delete_content', default=None,
                    help='Remove content from topic tree based on store local content file map'),
        make_option('-f', '--file-name', action='store', dest='file_name', default=None,
                    help='For testing, the name of the file to write as a sibling to topics.json'),
    )

    def handle(self, *args, **options):
        location = options.get("location")
        parent_path = options.get("parent_path")
        file_name = options.get("file_name")
        delete = options.get("delete_content")
        data_path = settings.DATA_PATH

        # We either add or remove content
        if int(bool(location)) + int(bool(delete)) != 1:
                raise CommandError("You must either add or delete content by specifing either -l or -d")

        # File name is used in adding and deleting, so it must exist
        if not file_name:
            raise CommandError("You must specify a filename.")

        # If adding content, check the criteria
        if location:
            if not os.path.exists(location):
                raise CommandError("The location given:'%s' does not exist on your computer.  Please enter a valid directory." % location)
            elif not parent_path:
                raise CommandError("You must specify a parent URL to insert/update the new node in the topic tree.")
            elif not get_topic_by_path(parent_path):
                raise CommandError("The base path:'%s' does not exist in the current topic tree. Please enter a valid parent path." % parent_path)
            elif int(bool(options["move"])) + int(bool(options["copy"])) != 1:
                raise CommandError("You must specify one flag to copy content (--copy) or move content (--move)")
            else:
                logging.info("Compiling data from %s for insertion to %s ..." % (location, parent_path))
                add_content(location, parent_path, copy_files=options["copy"], file_name=file_name)
                logging.info("Successfully added content bundle %s" % location)

        elif delete:
            if file_name == "topics.json":
                raise CommandError("You cannot delete the topic tree wildman. Watch your typing fingers.")
            elif not os.path.exists(os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name)):
                raise CommandError("The file name '%s' does not exist. Please specify a valid file name." % file_name)
            else: 
                logging.info("Deleting content mapped in '%s'" % file_name)
                remove_content(file_name)
                logging.info("Successfully removed content bundle %s" % file_name)


def add_content(location, parent_path, copy_files=True, file_name=None):
    """
    Take a "root" location and add content to system by mapping file
    hierarchy to JSON, copying content into the local_content directory,
    and updating the topic tree with the mapping inserted.
    """
    ensure_dir(LOCAL_CONTENT_ROOT)

    def construct_node(location, parent_path):
        """Return list of dictionaries of subdirectories and/or files in the location"""
        # Recursively add all subdirectories
        children = []
        base_name = os.path.basename(trim_slash(location))
        topic_slug = slugify(base_name)
        current_path = add_slash(os.path.join(parent_path, topic_slug))
        node= {
            "kind": "Topic",
            "path": current_path,
            "id": topic_slug,
            "title": humanize_name(base_name),
            "slug": topic_slug,
            "description": "",
            "parent_id": os.path.basename(parent_path[:-1]),
            "ancestor_ids": filter(None, parent_path.split("/")),  # TODO(bcipolli) get this from the parent node directly
            "hide": False,
            "children": [construct_node(os.path.join(location, s), current_path) for s in os.listdir(location) if os.path.isdir(os.path.join(location, s))],
        }

        # Add all files
        files = [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))]
        for full_filename in files:
            kind = get_kind_by_extension(full_filename)

            filename = os.path.splitext(full_filename)[0]
            extension = os.path.splitext(full_filename)[1].lower()
            file_slug = slugify(filename)
            node["children"].append({
                "youtube_id": file_slug,
                "id": file_slug,
                "title": humanize_name(filename),
                "path": os.path.join(current_path, file_slug),
                "path": add_slash(os.path.join(current_path, file_slug)),
                "ancestor_ids": filter(None, current_path.split("/")),
                "slug": file_slug,
                "parent_id": os.path.basename(topic_slug),
                "kind": kind,
            })

            # Copy over content
            normalized_filename = "%s%s" % (file_slug, extension)
            file_fn = shutil.copy if copy_files else shutil.move
            file_fn(os.path.join(location, full_filename), os.path.join(LOCAL_CONTENT_ROOT, normalized_filename))
            logging.debug("%s file %s to local content directory." % ("Copied" if copy_files else "Moved", normalized_filename))

        # Finally, can add contains
        contains = set([])
        for ch in node["children"]:
            contains = contains.union(ch.get("contains", set([])))
            contains = contains.union(set([ch["kind"]]))
        node["contains"] = list(contains)

        return node

    def inject_topic_tree(new_node, parent_path, data_path=settings.DATA_PATH):
        """Insert all local content into topic_tree"""
        # Update portion of topic tree
        old_node = get_topic_by_path(new_node["path"])
        if old_node:
            logging.info("Updating node at path %s" % new_node["path"])
            old_node.update(new_node)
        else:
            logging.info("Inserting path %s as child of path %s" % (new_node["path"], parent_path))
            parent_node = get_topic_by_path(parent_path)
            parent_node["children"].append(new_node)

        # Write updated topic tree to disk
        rewrite_topic_tree()

    # First, generate new topic_tree from file hierarchy
    nodes = construct_node(location, parent_path)

    # Next, write it to disk for future reference
    if file_name:
        ensure_dir(settings.LOCAL_CONTENT_DATA_PATH)
        write_location = os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name)
        with open(write_location, "w") as dumpsite:
            json.dump(nodes, dumpsite, indent=4)
        logging.info("Wrote output to %s" % write_location)

    # Finally, update master topic tree with desired mapping
    inject_topic_tree(nodes, parent_path)


def remove_content(file_name, data_path=settings.DATA_PATH):
    """
    Remove content from the system by deleting the mapping,
    deleting any content contained in the mapping from the content
    directory, and eing the topic_tree to it's former glory.
    """

    def restore_topic_tree(local_content):
        """Remove local_content from topics.json"""
        try:
            node = get_topic_by_path(local_content["path"])
            # NOTE: del node here didn't work, hence the solution below -- works but not pretty
            parent = get_parent(node)
            if not parent: # i.e. is root
                topic_tree = get_topic_tree()
                topic_tree["children"][:] = [child for child in topic_tree["children"] if child.get('id') != local_content["id"]]
            else:
                parent["children"][:] = [child for child in parent["children"] if child.get('id') != local_content["id"]]
        except:
            raise CommandError("Failed to delete %s from topic tree" % local_content["path"])
        else:
            rewrite_topic_tree()
            logging.info("Successfully removed %s from topic tree" % local_content["path"])

    def delete_content_files(local_content):
        """Remove local content videos from content directory"""
        videos = get_all_leaves(local_content, "Video")
        videos_deleted = 0 
        for v in videos:
            # TODO (we should ensure that we are storing unique filenames, and we should store that in the local content)
            possible_videos = glob.glob(os.path.join(settings.LOCAL_CONTENT_ROOT, "%s.*" % v["slug"]))
            assert len(possible_videos) == 1, "Crap, we have a duplicate filename. Too late now!"
            os.remove(os.path.join(settings.LOCAL_CONTENT_ROOT, possible_videos[0]))
            videos_deleted += 1
        logging.info("Deleted %d videos from the local content directory" % videos_deleted)

    with open(os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name)) as f:
        local_content = json.load(f)
    # Extract local node from topic tree
    restore_topic_tree(local_content)
    # Delete files from content dir
    delete_content_files(local_content)
    # Delete local file map
    os.remove(os.path.join(settings.LOCAL_CONTENT_DATA_PATH, file_name))
    logging.info("Deleted local content map %s" % file_name)


# Helper functions
def trim_slash(path):
    return path if not path or path[-1] != "/" else path[:-1]

def add_slash(path):
    return path if not path or path[-1] == "/" else (path + "/")

def rewrite_topic_tree():
    """Write topic tree from memory to disk"""
    topic_tree = get_topic_tree()
    topic_file_path = os.path.join(settings.DATA_PATH, topics_file)
    with open(topic_file_path, 'w') as f:
        json.dump(topic_tree, f, indent=4)
    logging.info("Rewrote topic tree: %s" % topic_file_path)
