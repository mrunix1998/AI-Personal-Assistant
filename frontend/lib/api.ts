export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export function getToken() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('access_token') || '';
}

export function setToken(value: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('access_token', value);
}

export function clearToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const accessToken = getToken();

  const inputHeaders = (options.headers || {}) as Record<string, string>;
  const headers: Record<string, string> = {
    ...inputHeaders,
  };

  const hasBody = options.body !== undefined && options.body !== null;
  if (hasBody && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const contentType = res.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await res.json()
    : await res.text();

  if (!res.ok) {
    const message =
      typeof data === 'string'
        ? data
        : data?.detail
          ? typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail)
          : JSON.stringify(data);

    throw new Error(message);
  }

  return data;
}

export async function api(path: string, options: RequestInit = {}) {
  try {
    const data = await apiFetch(path, options);
    return { ok: true, data };
  } catch (error: any) {
    return {
      ok: false,
      message: error?.message || String(error),
      data: null,
    };
  }
}
