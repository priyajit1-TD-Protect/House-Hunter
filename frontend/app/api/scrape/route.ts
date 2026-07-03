import { NextResponse } from "next/server";

const API = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    const res = await fetch(`${API}/api/scrape`, { method: "POST" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Failed to reach API" }, { status: 502 });
  }
}
