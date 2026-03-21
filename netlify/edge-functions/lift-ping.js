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

  const cookie = Deno.env.get('LIFT_SESSION_COOKIE');
  const timestamp = new Date().toISOString();

  // Check 1 — env var present?
  if (!cookie) {
    return new Response(JSON.stringify({
      status: 'error',
      timestamp,
      checks: {
        env_var: { pass: false, message: 'LIFT_SESSION_COOKIE is not set in Netlify environment variables' },
        lift_reachable: { pass: null, message: 'Skipped — no cookie to test with' },
        session_valid: { pass: null, message: 'Skipped — no cookie to test with' },
      },
      action_required: 'Add LIFT_SESSION_COOKIE to Netlify environment variables'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://paramountprints-dash.netlify.app',
      }
    });
  }

  // Check 2 — use the lightest CSV we have (Machine_Type is small)
  const testUrl = 'https://bny.lifterp.com/ords/lift/erp/flush/ondemand/1162/Machine_Type/Machine_Type.csv';

  let liftReachable = false;
  let sessionValid = false;
  let rowCount = 0;
  let errorMessage = null;
  let responseStatus = null;

  try {
    const response = await fetch(testUrl, {
      headers: {
        'Cookie': `ORA_WWV_APP_100=${cookie}`,
        'Accept': 'text/csv,*/*',
        'User-Agent': 'ParamountPrints-Dashboard/1.0',
      }
    });

    responseStatus = response.status;
    liftReachable = true;

    const body = await response.text();

    // Detect expired session (LIFT redirects to login HTML)
    if (body.trim().startsWith('<!DOCTYPE') || body.trim().startsWith('<html')) {
      sessionValid = false;
      errorMessage = 'LIFT returned an HTML login page — session cookie is expired';
    } else if (!response.ok) {
      sessionValid = false;
      errorMessage = `LIFT returned HTTP ${response.status}`;
    } else {
      sessionValid = true;
      // Count rows (subtract 1 for header)
      rowCount = body.trim().split('\n').length - 1;
    }

  } catch (err) {
    liftReachable = false;
    errorMessage = `Network error reaching LIFT: ${err.message}`;
  }

  const allGood = liftReachable && sessionValid;

  const result = {
    status: allGood ? 'ok' : 'error',
    timestamp,
    checks: {
      env_var: {
        pass: true,
        message: `LIFT_SESSION_COOKIE is set (${cookie.length} chars)`
      },
      lift_reachable: {
        pass: liftReachable,
        message: liftReachable
          ? `LIFT responded with HTTP ${responseStatus}`
          : errorMessage
      },
      session_valid: {
        pass: sessionValid,
        message: sessionValid
          ? `Session active — Machine_Type CSV returned ${rowCount} rows`
          : (errorMessage || 'Session invalid')
      }
    }
  };

  if (!allGood) {
    result.action_required = sessionValid === false
      ? 'Refresh ORA_WWV_APP_100 in DevTools → update LIFT_SESSION_COOKIE in Netlify env vars → redeploy'
      : errorMessage;
  }

  return new Response(JSON.stringify(result, null, 2), {
    status: allGood ? 200 : 503,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': 'https://paramountprints-dash.netlify.app',
      'Cache-Control': 'no-store',
    }
  });
};

export const config = {
  path: '/api/lift/ping',
};
