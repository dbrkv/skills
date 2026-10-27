// Client-side code: everything here ships to the browser bundle.
const SECRET = process.env.STRIPE_SECRET_KEY;

export async function charge(cardToken, amount) {
  const res = await fetch('https://api.stripe.com/v1/charges', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${SECRET}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({ source: cardToken, amount: String(amount) }),
  });
  return res.json();
}
