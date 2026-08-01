# X/Twitter Article Capture — Quick Reference

## fxtwitter API for Articles

Twitter Articles (long-form posts) use draft.js block format, NOT `tweet.text`.

### Endpoint
```bash
curl -sL "https://api.fxtwitter.com/{handle}/status/{tweet_id}"
```

### Response Structure
```json
{
  "tweet": {
    "text": "",                    // EMPTY for Articles
    "article": {
      "title": "...",
      "preview_text": "...",
      "cover_media": {
        "media_info": {
          "original_img_url": "https://pbs.twimg.com/media/..."
        }
      },
      "content": {
        "blocks": [...],           // draft.js blocks
        "entityMap": [...]         // LIST, not dict!
      },
      "media_entities": [...]      // Image URLs live HERE
    }
  }
}
```

### Block Type → Markdown Mapping
| block.type | Output |
|---|---|
| `header-one` | `# text` |
| `header-two` | `## text` |
| `header-three` | `### text` |
| `unordered-list-item` | `- text` |
| `ordered-list-item` | `1. text` |
| `unstyled` | plain paragraph |
| `atomic` | check entityMap for images |

### ⚠️ Critical: entityMap is a LIST, not a dict
```python
entity_map = article['content']['entityMap']  # This is a list!
# NOT entity_map.keys() — that throws AttributeError
```

### ⚠️ Critical: Image URLs are in `media_entities[]`, NOT entityMap
```python
# Cover image
cover_url = article['cover_media']['media_info']['original_img_url']

# Body images (8-20 common in long Articles)
for me in article['media_entities']:
    url = me['media_info']['original_img_url']
    # Download with ?name=orig for full resolution
```

entityMap entities of type `MEDIA` only have `mediaItems[].mediaId` (numeric ID), no URL.

### Extraction Script Pattern
```python
import sys, json

data = json.load(sys.stdin)
article = data.get('tweet', {}).get('article', {})
blocks = article.get('content', {}).get('blocks', [])
entity_map = article.get('content', {}).get('entityMap', [])

# Build entity lookup from list
entity_lookup = {}
if isinstance(entity_map, list):
    for i, v in enumerate(entity_map):
        entity_lookup[i] = v

output = []
for block in blocks:
    btype = block.get('type', '')
    text = block.get('text', '')
    
    if btype == 'header-one':
        output.append(f'# {text}')
    elif btype == 'header-two':
        output.append(f'## {text}')
    elif btype == 'header-three':
        output.append(f'### {text}')
    elif btype == 'unordered-list-item':
        output.append(f'- {text}')
    elif btype == 'ordered-list-item':
        output.append(f'1. {text}')
    elif btype == 'atomic':
        for er in block.get('entityRanges', []):
            ent = entity_lookup.get(er.get('key', -1), {})
            if ent.get('type') == 'IMAGE':
                src = ent.get('data', {}).get('src', '')
                if src:
                    output.append(f'![image]({src})')
    else:
        if text.strip():
            output.append(text)

print('\n\n'.join(output))
```

### Article Metadata
- `tweet.article.title` — article title
- `tweet.article.preview_text` — preview/summary
- `tweet.article.cover_media.media_info.original_img_url` — cover image
- `tweet.author.name` / `tweet.author.screen_name` — author info
- `tweet.likes`, `tweet.retweets`, `tweet.views` — engagement metrics

### When `tweet.text` is Empty
If `tweet.text` is empty or just a t.co link, check for `tweet.article` — it's a long-form Article, not a regular tweet. Extract from `blocks[]` instead.
