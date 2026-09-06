import DOMPurify from 'dompurify';

export function sanitizePreviewHtml(value: string) {
  return DOMPurify.sanitize(value, {
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'link', 'meta'],
    FORBID_ATTR: ['srcdoc'],
  });
}

export function plainTextPreview(value: string) {
  const container = document.createElement('div');
  for (const paragraph of value.split(/\n\s*\n/).filter(Boolean)) {
    const p = document.createElement('p');
    p.textContent = paragraph;
    container.appendChild(p);
  }
  return container.innerHTML;
}
