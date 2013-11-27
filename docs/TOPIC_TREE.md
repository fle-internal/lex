# Understanding the Topic Tree 
## (or: how to hack together a local content injection!)

El topic tree. It's the lifeblood of KA Lite. It is one _big_ json file (located: `static/data/topics.json`) that holds the key to the hierarchical relationships between topics, videos, and exercises, and also contains metadata on for each. 


## Topic Tree Structure

In order to begin the process of modifying KA Lite to accept non-KA content, we first must understand how the topic tree is structured. 

Three import types of "nodes" (which are dictionaries of meta-data): __Topic, Video, and Exercise__. Topics (e.g. Math) have "children" which are more nodes. What follows is a breakdown of the meta data in each node.

## Topic node 
### Contains the following meta: 

```
{ 
  "icon_src": "", # path to icon
  "path": "/", # internal mapping path (this is the root topic, so it's at the root directory)
  "id": "root", # unique id
  "hide": true, # whether this should be shown or not 
  "title": "Khan Academy", # display title 
  "contains": [ # list of all node types this contains
    "Topic", 
    "Video", 
    "Exercise"
  ], 
  "children":[ # every child node is contained in this list
    "icon_src": "", 
    "path": "/math/", # it increments from root
    "id": "math", 
    "hide": false, 
    "title": "Math", 
    "contains": [
      "Topic", 
      "Video", 
      "Exercise"
    ], 
    "children": [ ... ], # and so this continues!
    "parent_id": "root", # parent is root because this is a top level topic
    "in_knowledge_map": false, 
    "ancestor_ids": [
      "root"
    ], 
    "description": null, 
    "x_pos": 0.0, 
    "node_slug": "math", 
    "kind": "Topic", 
    "topic_page_url": null, # null b/c shown on topic page (e.g. "/math/algebra/solving-linear-equations-and-inequalities") 
    "extended_slug": "math", # full path plus slug (e.g. "math/algebra/solving-linear-equations-and-inequalities")
    "slug": "math", # url friendly id (e.g. "solving-linear-equations-and-inequalities")
    "y_pos": 0.0
  ], 
  "parent_id": null, # the id of it's parent (this is the root topic, so no parent)
  "in_knowledge_map": false, # KA specific
  "ancestor_ids": [], # a list of all parent's parent ids, all the way up to the top
  "description": "", # optional description of the node
  "x_pos": 0.0, # looks like this is only non-zero in frequently -- guessing it's used for knowledgemap positioning
  "node_slug": "root", # url safe identifier
  "kind": "Topic", # one of three node tpyes (topic, video, exercise)
  "topic_page_url": null, # actual url from the topic page
  "extended_slug": null, # full path plus slug (e.g. math/power-mode/some-exercise-name)
  "slug": "", # url friendly id (e.g. "some-exercise-name ")
  "y_pos": 0.0 # looks like this is only non-zero in frequently -- guessing it's used for knowledgemap positioning
}
```

## Video nodes
### Contain the following meta:

```
{
  "duration": 462, # length of video
  "related_exercise": { # info on how to find related exercise
    "path": "/math/arithmetic/addition-subtraction/basic_addition/e/addition_1/", 
    "title": "1-digit addition", 
    "id": "addition_1", 
    "slug": "addition_1"
  }, 
  "download_urls": { # where to download the video and screenshot
    "mp4": "http://s3.amazonaws.com/KA-youtube-converted/AuX7nPBqDts.mp4/AuX7nPBqDts.mp4", 
    "png": "http://s3.amazonaws.com/KA-youtube-converted/AuX7nPBqDts.mp4/AuX7nPBqDts.png", 
    "m3u8": "http://s3.amazonaws.com/KA-youtube-converted/AuX7nPBqDts.m3u8/AuX7nPBqDts.m3u8"
  }, 
  "id": "AuX7nPBqDts", # unique id
  "title": "Basic addition", # human readable title
  "parent_id": "basic_addition", # parent in the topic tree
  "ancestor_ids": [ # list of all parent's parents
    "root", 
    "math", 
    "arithmetic", 
    "addition-subtraction", 
    "basic_addition"
  "description": "Introduction to addition. Multiple visual ways to represent addition.", # optional desc.
  "path": "/math/arithmetic/addition-subtraction/basic_addition/v/basic-addition/", # Note the 'v'
  "slug": "basic-addition", # url friendly unique id
  "kind": "Video", # obvi
  "keywords": "Math, Addition, Khan, Academy, CC_1_OA_1, CC_1_OA_2, CC_1_OA_3, CC_1_OA_6", # optional
  "youtube_id": "AuX7nPBqDts", # same as ID above.. 
  "readable_id": "basic-addition" # same as slug
}, 
```

## Exercise Nodes 
### Contain the following meta:

```
{
  "v_position": -1, # ??
  "path": "/math/arithmetic/addition-subtraction/basic_addition/e/addition_1/", # Note the 'e'
  "id": "addition_1", # unique id
  "display_name": "1-digit addition", # to be displayed 
  "title": "1-digit addition", # not sure the difference between this and display name
  "parent_id": "basic_addition", # 
  "live": true, # to show, or not to show
  "ancestor_ids": [
    "root", 
    "math", 
    "arithmetic", 
    "addition-subtraction", 
    "basic_addition"
  ], 
  "related_video_slugs": [
    "basic-addition"
  ], 
  "description": "Add two numbers from 1 to\u00a010", 
  "basepoints": 10.0, 
  "h_position": 0, 
  "slug": "addition_1", 
  "kind": "Exercise", 
  "name": "addition_1", 
  "seconds_per_fast_problem": 4.0, 
  "prerequisites": [], 
  "exercise_id": "addition_1"
},
```

## Now that we know the basic structure, how is it being used? Assuming that's the important stuff, how do we insert it?

Files involved:

* `topics.json # the actual topic tree data file`
* `topic_tools.py # Important constants and helpful functions for topic tree` 
* `main/views.py > splat_handler(request, splat) # Filters requests of the topic tree`

So basically, a url is requested, get's plugged into `splat_handler`, which utilizes the topic tree structure to spit out the correct page. To know how we should insert data into the topic tree, we need to first know how `splat_handler` uses the data (marked up below)

```
def splat_handler(request, splat):
    slugs = filter(lambda x: x, splat.split("/")) # parses the url that has been passes
    current_node = topicdata.TOPICS # topic_tools.get_topic_tree() which returns the entire topic tree as a dictionary
    seeking = "Topic" # search for topics, until we find videos or exercise
    for slug in slugs:
        # towards the end of the url, we switch from seeking a topic node
        #   to the particular type of node in the tree
        # kind_slugs = hardcoded list of kinds: kind_slugs = {"Video": "v/", "Exercise": "e/", "Topic": ""}
        # an /e/ in url says "look for exercise" and a /v/ says "look for video". 
        # No e or v? We're looking for a topic.
        for kind, kind_slug in topic_tools.kind_slugs.items(): 
            if slug == kind_slug.split("/")[0]:
                seeking = kind
                break

        # match each step in the topics hierarchy, with the url slug.
        else:
            # build up a list of all children of the same kind
            children = [child for child in current_node['children'] if child['kind'] == seeking]
            if not children:
                raise Http404
            match = None
            prev = None
            next = None
            # Iterates through them, simply looking for a slug match -- slugs are important!
            for child in children:
                if match:
                    next = child
                    break
                if child["slug"] == slug:
                    match = child
                else:
                    prev = child
            if not match:
                raise Http404
            current_node = match
            # to be continued... 
```
if it finds the match, it sends it to it's respective handlers. Let's take a closer look at these handlers to know what 
else, beyond slugs, is important
```
    # continued from above: 
    if current_node["kind"] == "Topic":
        return topic_handler(request, current_node)
    elif current_node["kind"] == "Video":
        return video_handler(request, video=current_node, prev=prev, next=next)
    elif current_node["kind"] == "Exercise":
        return exercise_handler(request, current_node)
    else:
        raise Http404
```

### If we match a topic it gets handled by `topic_handler`

```
# just rendering to the `topic.html` template and returning the result of the `topic_context` function! Let's look there
@backend_cache_page
@render_to("topic.html")
def topic_handler(request, topic):
    return topic_context(topic)

def topic_context(topic):
    """
    Given a topic node, create all context related to showing that topic
    in a template.
    """
    # Returning the top level videos, exercises, and topics
    # Given a topic node, returns all video node children (non-recursively)
    videos    = topic_tools.get_videos(topic)
    # Given a topic node, returns all exercise node children (non-recursively)
    exercises = topic_tools.get_exercises(topic) # NOTE: 'live' is important
    # Given a topic node, returns all children that are not hidden and contain at least one video (non-recursively)
    topics    = topic_tools.get_live_topics(topic) # NOTE: 'hide' is important

    # Get video counts if they'll be used, on-demand only.
    # Check in this order so that the initial counts are always updated
    # video_counts_need_update: Compare current state to global state variables to check whether video counts need updating.
    # get_video_counts: Uses the (json) topic tree to query the django database for which video files exist
    if video_counts_need_update() or not 'nvideos_local' in topic:
        (topic,_,_) = get_video_counts(topic=topic, videos_path=settings.CONTENT_ROOT)

    my_topics = [dict((k, t[k]) for k in ('title', 'path', 'nvideos_local', 'nvideos_known')) for t in topics]

    context = {
        "topic": topic,
        "title": topic["title"],
        "description": re.sub(r'<[^>]*?>', '', topic["description"] or ""),
        "videos": videos,
        "exercises": exercises,
        "topics": my_topics,
        "backup_vids_available": bool(settings.BACKUP_VIDEO_SOURCE),
    }
    return context
```

#### Based on the above functions, topics nodes need the following meta in the topic tree:
- slug
- kind
- children
- title
- description
- hide

(and we should likely also store the following):

- path
- id
- contains 
- parent_id
- ancestor_ids 
- node_slug
- topic_page_url
- extended_slug

(we knowingly won't be storing the following for now):
- icon_src
- in_knowledge_map  
- x_pos 
- y_pos


### If we match a video it gets handled by `video_handler`
```
@backend_cache_page
@render_to("video.html")
def video_handler(request, video, format="mp4", prev=None, next=None):

    video_on_disk = is_video_on_disk(video['youtube_id']) # Checks if it's in the content dir
    video_exists = video_on_disk or bool(settings.BACKUP_VIDEO_SOURCE)

    if not video_exists:
        if request.is_admin:
            # TODO(bcipolli): add a link, with querystring args that auto-checks this video in the topic tree
            messages.warning(request, _("This video was not found! You can download it by going to the Update page."))
        elif request.is_logged_in:
            messages.warning(request, _("This video was not found! Please contact your teacher or an admin to have it downloaded."))
        elif not request.is_logged_in:
            messages.warning(request, _("This video was not found! You must login as an admin/teacher to download the video."))

    video["stream_type"] = "video/%s" % format

    if video_exists and not video_on_disk:
        messages.success(request, "Got video content from %s" % video["stream_url"])

    context = {
        "video": video,
        "title": video["title"],
        "prev": prev,
        "next": next,
        "backup_vids_available": bool(settings.BACKUP_VIDEO_SOURCE),
        "use_mplayer": settings.USE_MPLAYER and is_loopback_connection(request),
    }
    return context
```

#### Based on the above functions, topics nodes need the following meta in the topic tree:
- youtube_id
- title

(and we should likely also store the following):

- path
- id
- slug
- parent_id
- ancestor_ids
- kind  

(we knowingly won't be storing the following for now):
- duration
- related_exercise
- download_urls
- keywords
- readable_id
- description 


### If we match a exercise it gets handled by `exercise_handler`
```
@backend_cache_page
@render_to("exercise.html")
def exercise_handler(request, exercise):
    """
    Display an exercise
    """
    # Find related videos
    related_videos = {}
    for slug in exercise["related_video_slugs"]:
        video_nodes = topicdata.NODE_CACHE["Video"].get(topicdata.SLUG2ID_MAP.get(slug), None)

        # Make sure the IDs are recognized, and are available.
        if not video_nodes:
            continue
        if not video_nodes[0].get("on_disk", False) and not settings.BACKUP_VIDEO_SOURCE:
            continue

        # Search for a sibling video node to add to related exercises.
        for video in video_nodes:
            if topic_tools.is_sibling({"path": video["path"], "kind": "Video"}, exercise):
                related_videos[slug] = video
                break

        # failed to find a sibling; just choose the first one.
        if slug not in related_videos:
            related_videos[slug] = video_nodes[0]

    context = {
        "exercise": exercise,
        "title": exercise["title"],
        "exercise_template": "exercises/" + exercise["slug"] + ".html",
        "related_videos": related_videos.values(),
    }
    return context
```

#### Based on the above functions, exercise nodes need the following meta in the topic tree:
(we aren't going to be storing anything related to exercises right now, so leaving this to be filled in later.)

