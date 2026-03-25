const BASE_URL = 'https://bny.lifterp.com/ords/lift/erp/flush/ondemand/1162';

export default async (request, context) => {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
      }
    });
  }

  const timestamp = new Date().toISOString();
  const testUrl = `${BASE_URL}/OnHandYards/OnHandYards.csv`;

  let liftReachable = false;
  let dataValid = false;
  let rowCount = 0;
  let responseStatus = null;
  let errorMessage = null;

  try {
    const response = await fetch(testUrl, {
      headers: {
        'Accept': 'text/csv,*/*',
        'User-Agent': 'ParamountPrints-Dashboard/1.0',
      }
    });

    responseStatus = response.status;
    liftReachable = response.ok;

    if (response.ok) {
      const body = await response.text();

      if (body.trim().startsWith('<!DOCTYPE') || body.trim().startsWith('<html')) {
        dataValid = false;
        errorMessage = 'LIFT returned HTML instead of CSV';
      } else {
        dataValid = true;
        rowCount = body.trim().split('\n').length - 1;
      }
    } else {
      errorMessage = `LIFT returned HTTP ${response.status}`;
    }

  } catch (err) {
    liftReachable = false;
    errorMessage = `Network error: ${err.message}`;
  }

  const allGood = liftReachable && dataValid;

  const result = {
    status: allGood ? 'ok' : 'error',
    timestamp,
    endpoint_tested: testUrl,
    checks: {
      lift_reachable: {
        pass: liftReachable,
        message: liftReachable
          ? `LIFT responded HTTP ${responseStatus}`
          : (errorMessage || 'Unreachable')
      },
      data_valid: {
        pass: dataValid,
        message: dataValid
          ? `OnHandYards returned ${rowCount} rows`
          : (errorMessage || 'Invalid response')
      }
    },
    available_endpoints: [
      'orders', 'products', 'shipments', 'po', 'po_details',
      'shipmentshub', 'invoiceshub', 'printJobs',
      'InvoiceSummary', 'CreditSummary', 'InvoiceAdjustments', 'OnHandYards'
    ]
  };

  if (!allGood) {
    result.action_required = errorMessage;
  }

  return new Response(JSON.stringify(result, null, 2), {
    status: allGood ? 200 : 503,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-store',
    }
  });
};

export const config = {
  path: '/api/lift/ping',
};
