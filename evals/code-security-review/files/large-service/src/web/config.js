export const apiKey = process.env.VITE_PAYMENTS_KEY;
export async function call(path, opts) {
  const r = await fetch(`${API_BASE}/${path}`, { ...opts, headers: { 'X-Key': apiKey } });
  return r.json();
}
