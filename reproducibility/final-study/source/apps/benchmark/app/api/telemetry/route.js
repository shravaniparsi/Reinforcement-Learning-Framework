export const dynamic = 'force-dynamic';
export function GET() {
  return Response.json({ pid: process.pid, cpu: process.cpuUsage(), uptime: process.uptime() },
    { headers: { 'Cache-Control': 'no-store' } });
}
