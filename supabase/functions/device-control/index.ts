import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// Device pairing was retired at the owner's request. Keep this endpoint fail-closed
// so stale clients or old pairing links cannot create credentials or send heartbeats.
Deno.serve((_request: Request) => new Response(
  JSON.stringify({ error: "Device pairing has been permanently retired." }),
  {
    status: 410,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": "https://shayaanfarsheed-cmd.github.io",
      "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    },
  },
));
