export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export async function authRequest<T>(path: string, body: unknown): Promise<T> {
  const token = sessionStorage.getItem('pt_token');
  const response = await fetch('/api' + path, {
    method: 'POST', cache: 'no-store',
    headers: {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})},
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(typeof data.detail === 'string' ? data.detail : 'Please check your details and try again.', response.status);
  return data;
}
export function parseInvitation(value: string): string {
  value = value.trim();
  if (/^[A-Za-z0-9_-]{20,200}$/.test(value)) return value;
  try {
    const token = new URLSearchParams(new URL(value, location.origin).hash.slice(1)).get('token');
    if (token && /^[A-Za-z0-9_-]{20,200}$/.test(token)) return token;
  } catch {}
  throw new Error('Paste a complete invitation link or a valid invitation code.');
}
