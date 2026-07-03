import { NextRequest, NextResponse } from "next/server";

const API = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  try {
    const res = await fetch(`${API}/api/listings?${qs}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) {
      return NextResponse.json({ error: "Upstream error" }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: "Failed to reach API" }, { status: 502 });
  }
}
