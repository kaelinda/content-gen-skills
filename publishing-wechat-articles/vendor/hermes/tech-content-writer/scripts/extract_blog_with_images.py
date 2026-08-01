#!/usr/bin/env python3
"""
Extract tech blog content with images from browser.

Usage:
    1. Open blog URL with browser_navigate
    2. Run this IIFE in browser_console:
    
    (() => {
      const article = document.querySelector('article') || document.querySelector('main') || document.body;
      const result = [];
      const images = [];
      
      const walk = (node) => {
        if (node.nodeType === 3) { 
          const t = node.textContent.trim(); 
          if (t) result.push(t); 
          return; 
        }
        if (node.nodeType !== 1) return;
        
        const tag = node.tagName.toLowerCase();
        
        if (tag === 'img') {
          const src = node.getAttribute('src');
          const alt = node.getAttribute('alt') || '';
          if (src && src.startsWith('http')) {
            images.push({ src, alt });
            result.push(`![${alt}](${src})`);
          }
          return;
        }
        
        if (tag === 'h1') result.push('\n# ' + node.textContent.trim());
        else if (tag === 'h2') result.push('\n## ' + node.textContent.trim());
        else if (tag === 'h3') result.push('\n### ' + node.textContent.trim());
        else if (tag === 'pre') result.push('\n```\n' + node.textContent.trim() + '\n```');
        else if (tag === 'p') result.push(node.textContent.trim());
        else if (tag === 'ul' || tag === 'ol') {
          node.querySelectorAll(':scope > li').forEach(li => result.push('- ' + li.textContent.trim()));
        }
        else if (tag === 'blockquote') result.push('> ' + node.textContent.trim());
        else if (tag === 'figure') {
          const imgs = node.querySelectorAll('img');
          imgs.forEach(img => {
            const src = img.getAttribute('src');
            const alt = img.getAttribute('alt') || '';
            if (src && src.startsWith('http')) {
              images.push({ src, alt });
              result.push(`![${alt}](${src})`);
            }
          });
          const caption = node.querySelector('figcaption');
          if (caption) result.push('*' + caption.textContent.trim() + '*');
        }
        else { 
          for (const child of node.childNodes) walk(child); 
        }
      };
      
      walk(article);
      
      return {
        content: result.join('\n\n'),
        images: images
      };
    })()

    3. Parse the returned JSON:
       - content: markdown-formatted text with image links
       - images: array of {src, alt} objects
    
    4. When writing the article, embed images using the original URLs:
       ![alt text](https://original-url.com/image.png)
    
    5. Images will be preserved in the final HTML and visible in WeChat.

Notes:
    - Works for most tech blogs (Kimi, OpenAI, Anthropic, etc.)
    - Handles <figure> tags with <figcaption>
    - Preserves image order relative to text
    - Returns both content and metadata for verification
"""
