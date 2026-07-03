import { NextResponse } from "next/server";

const API = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API}/api/neighbourhoods`, { next: { revalidate: 3600 } });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json([], { status: 502 });
  }
}
