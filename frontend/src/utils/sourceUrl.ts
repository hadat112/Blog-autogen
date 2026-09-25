export function normalizeSourceUrl(value: string): string {
  const trimmed = value.trim();
  try {
    const url = new URL(trimmed);
    url.searchParams.delete('fbclid');
    return url.toString();
  } catch {
    return trimmed;
  }
}
