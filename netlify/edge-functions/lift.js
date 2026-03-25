const BASE_URL = 'https://bny.lifterp.com/ords/lift/erp/flush/ondemand/1162';

// Valid LIFT endpoints
const VALID_ENDPOINTS = [
  'products',
  'orders',
  'shipments',
  'po',
  'shipmentshub',
  'InvoiceAdjustments',
  'invoiceshub',
  'printJobs',
  'InvoiceSummary',
  'CreditSummary',
  'OnHandYards',
  'po_details',
];

export default async (request, context) => {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }

  const url = new URL(request.url);
  const pathParts = url.pathname.split('/');
  const name = pathParts[pathParts.length - 1];

  if (!name || name === 'lift') {
    return new Response(JSON.stringify({
      error: 'Missing endpoint name.',
      valid_endpoints: VALID_ENDPOINTS,
      usage: '/api/lift/{endpoint}  e.g. /api/lift/orders'
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  // Case-insensitive match against valid endpoints
  const matched = VALID_ENDPOINTS.find(e => e.toLowerCase() === name.toLowerCase());
  if (!matched) {
    return new Response(JSON.stringify({
      error: `Unknown endpoint: ${name}`,
      valid_endpoints: VALID_ENDPOINTS
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  const liftUrl = `${BASE_URL}/${matched}/${matched}.csv`;

  try {
    const response = await fetch(liftUrl, {
      headers: {
        'Accept': 'text/csv,*/*',
        'User-Agent': 'ParamountPrints-Dashboard/1.0',
      }
    });

    if (!response.ok) {
      return new Response(JSON.stringify({
        error: `LIFT returned HTTP ${response.status}`,
        url: liftUrl
      }), {
        status: response.status,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    const csv = await response.text();

    // Sanity check — if we got HTML back something is wrong
    if (csv.trim().startsWith('<!DOCTYPE') || csv.trim().startsWith('<html')) {
      return new Response(JSON.stringify({
        error: 'LIFT returned HTML instead of CSV',
        url: liftUrl
      }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    // Count rows for response header info
    const rowCount = csv.trim().split('\n').length - 1;

    return new Response(csv, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-store',
        'X-LIFT-Endpoint': matched,
        'X-LIFT-Rows': String(rowCount),
      }
    });

  } catch (err) {
    return new Response(JSON.stringify({
      error: `Proxy fetch failed: ${err.message}`,
      url: liftUrl
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
};

export const config = {
  path: '/api/lift/:name',
};
