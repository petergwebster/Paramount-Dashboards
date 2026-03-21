export default async (request, context) => {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': 'https://paramountprints-dash.netlify.app',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }

  const url = new URL(request.url);

  // Extract the CSV name from the path: /api/lift/Data_Orders_All
  const pathParts = url.pathname.split('/');
  const name = pathParts[pathParts.length - 1];

  if (!name || name === 'lift') {
    return new Response(JSON.stringify({ error: 'Missing CSV name. Usage: /api/lift/{CSVName}' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Cookie stored as full "name=value" pair in Netlify env var
  // e.g. LIFT_SESSION_COOKIE = "ORA_WWV-R15muB6cIPZZ4GVaomS-uSF1=ORA_WWV-R15muB6cIPZZ4GVaomS-uSF1"
  const cookie = Deno.env.get('LIFT_SESSION_COOKIE');

  if (!cookie) {
    return new Response(JSON.stringify({ error: 'LIFT_SESSION_COOKIE environment variable not set' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const liftUrl = `https://bny.lifterp.com/ords/lift/erp/flush/ondemand/1162/${name}/${name}.csv`;

  try {
    const response = await fetch(liftUrl, {
      headers: {
        'Cookie': cookie,
        'Accept': 'text/csv,*/*',
        'User-Agent': 'ParamountPrints-Dashboard/1.0',
      }
    });

    if (!response.ok) {
      return new Response(
        JSON.stringify({ error: `LIFT returned HTTP ${response.status}`, url: liftUrl }),
        {
          status: response.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const csv = await response.text();

    // Basic sanity check — if we got HTML back, the cookie is probably expired
    if (csv.trim().startsWith('<!DOCTYPE') || csv.trim().startsWith('<html')) {
      return new Response(
        JSON.stringify({
          error: 'LIFT returned HTML instead of CSV — session cookie is likely expired',
          fix: 'Refresh cookie in DevTools and update LIFT_SESSION_COOKIE in Netlify env vars as full name=value pair'
        }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    return new Response(csv, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Access-Control-Allow-Origin': 'https://paramountprints-dash.netlify.app',
        'Cache-Control': 'no-store',
        'X-LIFT-Source': liftUrl,
      }
    });

  } catch (err) {
    return new Response(
      JSON.stringify({ error: `Proxy fetch failed: ${err.message}` }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
};

export const config = {
  path: '/api/lift/:name',
};
