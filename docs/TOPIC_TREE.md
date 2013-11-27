# Understanding the Topic Tree 
## (or: how to hack together a local content injection!)

El topic tree. It's the lifeblood of KA Lite. It is one _big_ json file (located: `static/data/topics.json`) that holds the key to the hierarchical relationships between topics, videos, and exercises, and also contains metadata on each entry. 


## Topic Tree Structure

In order to begin the process of modifying KA Lite to accept non-KA content, we first must understand how the topic tree is structured. 

Three import types of "nodes": Topic, Video, Exercise

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
  "path": "/math/arithmetic/addition-subtraction/basic_addition/v/basic-addition/", # full internal path
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
  "path": "/math/arithmetic/addition-subtraction/basic_addition/e/addition_1/", # topic tree path
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

## Now, what meta is __truly__ important?
### For our purposes:

#### Meta that __topics__ need:
- path
- id
- hide (implicitly false -- this is only true ONCE in this whole json file)
- title (for now = ID)
- contains 
- children (obviously)
- parent_id
- ancestor_ids 
- node_slug
- kind
- topic_page_url
- extended_slug
- slug

Everything else can be added later if necessary. 

#### Meta that __videos__ need:
- id
- title
- parent_id 
- ancestor_ids
- path
- slug
- kind
- readable_id