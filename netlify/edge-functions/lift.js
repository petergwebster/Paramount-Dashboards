// netlify/edge-functions/lift.js
// Proxies requests to X-LIFT API endpoints, handling Oracle APEX session auth

const LIFT_BASE_URL = 'https://bny.lifterp.com';
const LIFT_LOGIN_URL = `${LIFT_BASE_URL}/ords/lift/lift/wwv_flow.accept`;
const LIFT_APP_ID = '100';

// Map of report names to their endpoint paths
const ENDPOINTS = {
  orders:             '/ords/lift/erp/flush/ondemand/1162/orders/orders.csv',
  products:           '/ords/lift/erp/flush/ondemand/1162/products/products.csv',
  shipments:          '/ords/lift/erp/flush/ondemand/1162/shipments/shipments.csv',
  shipmentshub:       '/ords/lift/erp/flush/ondemand/1162/shipmentshub/shipmentshub.csv',
  invoiceshub:        '/ords/lift/erp/flush/ondemand/1162/invoiceshub/invoiceshub.csv',
  InvoiceAdjustments: '/ords/lift/erp/flush/ondemand/1162/InvoiceAdjustments/InvoiceAdjustments.csv',
  InvoiceSummary:     '/ords/lift/erp/flush/ondemand/1162/InvoiceSummary/InvoiceSummary.csv',
  CreditSummary:      '/ords/lift/erp/flush/ondemand/1162/CreditSummary/CreditSummary.csv',
  OnHandYards:        '/ords/lift/erp/flush/ondemand/1162/OnHandYards/OnHandYards.csv',
  po:                 '/ords/lift/erp/flush/ondemand/1162/po/po.csv',
  printJobs:          '/ords/lift/erp/flush/ondemand/1162/printJobs/printJobs.csv',
};

async function getLiftSession(username, password) {
  // Step 1: GET the login page to obtain the initial session cookie + hidden form fields
  const loginPageRes = await fetch(`${LIFT_BASE_URL}/ords/lift/lift/f?p=${LIFT_APP_ID}:LOGIN`, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
  });

  // Extract session cookie from login page response
  const setCookieHeader = loginPageRes.headers.get('set-cookie') || '';
  const sessionCookieMatch = setCookieHeader.match(/ORA_WWV_APP_\d+=([^;]+)/);
  const initialCookie = sessionCookieMatch 
    ? `ORA_WWV_APP_${LIFT_APP_ID}=${sessionCookieMatch[1]}`
    : '';

  // Parse the login page HTML to get hidden form fields
  const loginPageHtml = await loginPageRes.text();
  
  // Extract p_flow_id, p_flow_step_id, p_instance from the form
  const flowIdMatch = loginPageHtml.match(/name="p_flow_id"\s+value="([^"]+)"/);
  const flowStepMatch = loginPageHtml.match(/name="p_flow_step_id"\s+value="([^"]+)"/);
  const instanceMatch = loginPageHtml.match(/name="p_instance"\s+value="([^"]+)"/);
  const pageSubmissionIdMatch = loginPageHtml.match(/name="p_page_submission_id"\s+value="([^"]+)"/);

  const p_flow_id = flowIdMatch ? flowIdMatch[1] : LIFT_APP_ID;
  const p_flow_step_id = flowStepMatch ? flowStepMatch[1] : '101';
  const p_instance = instanceMatch ? instanceMatch[1] : '0';
  const p_page_submission_id = pageSubmissionIdMatch ? pageSubmissionIdMatch[1] : '';

  // Step 2: POST login credentials
  const loginBody = new URLSearchParams({
    p_flow_id,
    p_flow_step_id,
    p_instance,
    p_page_submission_id,
    p_arg_names: 'P101_USERNAME',
    p_arg_values: username,
    p_t01: username,
    p_t02: password,
    p_md5_checksum: '',
    p_page_checksum: '',
  });

  const loginRes = await fetch(`${LIFT_BASE_URL}/ords/lift/lift/wwv_flow.accept`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Cookie': initialCookie,
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Origin': LIFT_BASE_URL,
      'Referer': `${LIFT_BASE_URL}/ords/lift/lift/f?p=${LIFT_APP_ID}:LOGIN`,
    },
    body: loginBody.toString(),
    redirect: 'manual', // Don't auto-follow — we need the cookie from the redirect response
  });

  // Extract the authenticated session cookie
  const authCookieHeader = loginRes.headers.get('set-cookie') || '';
  const authCookieMatch = authCookieHeader.match(/ORA_WWV_APP_\d+=([^;]+)/);
  
  if (!authCookieMatch) {
    // Try to get cookie from the initial response if redirect didn't set one
    return initialCookie || null;
  }

  return `ORA_WWV_APP_${LIFT_APP_ID}=${authCookieMatch[1]}`;
}

export default async function handler(req, context) {
  // CORS headers for Netlify dashboard
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  // Only allow GET
  if (req.method !== 'GET') {
    return new Response('Method not allowed', { status: 405, headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const report = url.searchParams.get('report');

    if (!report) {
      return new Response(JSON.stringify({ error: 'Missing ?report= parameter', available: Object.keys(ENDPOINTS) }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const endpoint = ENDPOINTS[report];
    if (!endpoint) {
      return new Response(JSON.stringify({ error: `Unknown report: ${report}`, available: Object.keys(ENDPOINTS) }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get credentials from Netlify environment variables
    const username = Netlify.env.get('LIFT_USERNAME');
    const password = Netlify.env.get('LIFT_PASSWORD');

    if (!username || !password) {
      return new Response(JSON.stringify({ error: 'LIFT_USERNAME or LIFT_PASSWORD not configured in Netlify env vars' }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get a fresh session cookie
    const sessionCookie = await getLiftSession(username, password);

    if (!sessionCookie) {
      return new Response(JSON.stringify({ error: 'Failed to authenticate with LIFT' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Fetch the CSV with the authenticated session
    const csvRes = await fetch(`${LIFT_BASE_URL}${endpoint}?`, {
      headers: {
        'Cookie': sessionCookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': `${LIFT_BASE_URL}/ords/lift/lift/f?p=${LIFT_APP_ID}:9900`,
      },
      redirect: 'follow',
    });

    if (!csvRes.ok) {
      return new Response(JSON.stringify({ error: `LIFT returned ${csvRes.status}` }), {
        status: csvRes.status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const csvData = await csvRes.text();

    // Validate we got actual CSV data (not an HTML login redirect)
    if (csvData.trim().startsWith('<')) {
      return new Response(JSON.stringify({ error: 'LIFT returned HTML — authentication may have failed' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    return new Response(csvData, {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'text/csv',
        'Cache-Control': 'no-cache',
        'X-Report': report,
        'X-Timestamp': new Date().toISOString(),
      }
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

export const config = {
  path: '/api/lift',
};
