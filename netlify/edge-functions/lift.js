// netlify/edge-functions/lift.js
// Proxies requests to X-LIFT API endpoints using session cookie auth

const LIFT_BASE_URL = 'https://bny.lifterp.com';

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

export default async function handler(req, context) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== 'GET') {
    return new Response('Method not allowed', { status: 405, headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const report = url.searchParams.get('report');

    if (!report) {
      return new Response(JSON.stringify({ 
        error: 'Missing ?report= parameter', 
        available: Object.keys(ENDPOINTS) 
      }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const endpoint = ENDPOINTS[report];
    if (!endpoint) {
      return new Response(JSON.stringify({ 
        error: `Unknown report: ${report}`, 
        available: Object.keys(ENDPOINTS) 
      }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get session cookie from Netlify environment variable
    const sessionCookie = Netlify.env.get('LIFT_SESSION_COOKIE');

    if (!sessionCookie) {
      return new Response(JSON.stringify({ 
        error: 'LIFT_SESSION_COOKIE not configured in Netlify env vars' 
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Fetch the CSV with the session cookie
    const csvRes = await fetch(`${LIFT_BASE_URL}${endpoint}?`, {
      headers: {
        'Cookie': sessionCookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': `${LIFT_BASE_URL}/ords/lift/lift/f?p=100:9900`,
      },
      redirect: 'follow',
    });

    if (!csvRes.ok) {
      return new Response(JSON.stringify({ 
        error: `LIFT returned ${csvRes.status}` 
      }), {
        status: csvRes.status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const csvData = await csvRes.text();

    // Check if we got HTML back (means session expired)
    if (csvData.trim().startsWith('<')) {
      return new Response(JSON.stringify({ 
        error: 'Session expired — update LIFT_SESSION_COOKIE in Netlify env vars' 
      }), {
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
