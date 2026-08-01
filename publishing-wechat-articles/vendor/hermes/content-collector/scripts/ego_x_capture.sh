#!/usr/bin/env bash
# ego-lite X/Twitter capture — extracts tweet content via real browser
# Usage: bash ego_x_capture.sh <tweet_url> [output_dir]
#
# Output: JSON with {author, text, images, datetime, engagement, thread}
# Saves raw JSON to output_dir/raw_ego.json

set -euo pipefail

URL="${1:?Usage: ego_x_capture.sh <tweet_url> [output_dir]}"
OUTPUT_DIR="${2:-/tmp/ego_capture_$(date +%s)}"

mkdir -p "$OUTPUT_DIR"

echo "[ego-lite] Capturing: $URL"
echo "[ego-lite] Output: $OUTPUT_DIR"

ego-browser nodejs <<HEREDOC
const task = await useOrCreateTaskSpace('ego_x_capture')
cliLog('task_space_id: ' + task.id)

await openOrReuseTab('$URL', { wait: true, timeout: 30 })
await waitForNetworkIdle({ timeout: 15 })

const data = await js(String.raw\`(() => {
  const article = document.querySelector('article')
  if (!article) return { error: 'no article found' }

  // Tweet text
  const tweetText = article.querySelector('[data-testid="tweetText"]')
  const text = tweetText ? tweetText.innerText : ''

  // Images
  const images = [...article.querySelectorAll('[data-testid="tweetPhoto"] img')]
    .map((img, i) => ({
      index: i,
      url: img.src,
      alt: img.alt || ''
    }))

  // Author
  const userName = article.querySelector('[data-testid="User-Name"]')
  const authorLines = userName ? userName.innerText.split('\\n') : []
  const author = {
    name: authorLines[0] || '',
    handle: authorLines[1] || ''
  }

  // Timestamp
  const time = article.querySelector('time')
  const datetime = time ? time.getAttribute('datetime') : ''

  // Engagement
  const getEngagement = (testId) => {
    const el = article.querySelector('[data-testid="' + testId + '"]')
    if (!el) return 0
    const ariaLabel = el.getAttribute('aria-label') || ''
    const match = ariaLabel.match(/([\d,.]+)\s/)
    return match ? match[1] : ariaLabel
  }

  const engagement = {
    replies: getEngagement('reply'),
    retweets: getEngagement('retweet'),
    likes: getEngagement('like'),
    bookmarks: getEngagement('bookmark'),
    views: (() => {
      const el = article.querySelector('a[href*="/analytics"]')
      if (!el) return '0'
      const text = el.innerText.trim()
      return text || '0'
    })()
  }

  return { author, text, images, datetime, engagement }
})()\`)

// Check for thread (scroll down to load replies, then extract)
const threadData = await js(String.raw\`(() => {
  const articles = document.querySelectorAll('article')
  if (articles.length <= 1) return { isThread: false, tweets: [] }

  const tweets = []
  for (const art of articles) {
    const tweetText = art.querySelector('[data-testid="tweetText"]')
    const userName = art.querySelector('[data-testid="User-Name"]')
    const authorLines = userName ? userName.innerText.split('\\n') : []
    const time = art.querySelector('time')

    if (tweetText) {
      tweets.push({
        author: authorLines[0] || '',
        handle: authorLines[1] || '',
        text: tweetText.innerText,
        datetime: time ? time.getAttribute('datetime') : ''
      })
    }
  }

  return { isThread: tweets.length > 1, tweets }
})()\`)

const result = {
  source_url: '$URL',
  captured_at: new Date().toISOString(),
  capture_method: 'ego-lite',
  ...data,
  thread: threadData
}

cliLog(JSON.stringify(result, null, 2))
HEREDOC

echo ""
echo "[ego-lite] Capture complete. Raw output above."
echo "[ego-lite] Output dir: $OUTPUT_DIR"
