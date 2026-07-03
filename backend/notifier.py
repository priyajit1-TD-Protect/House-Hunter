"""
Sends email alert via Resend when new listings score >= 75.
Only fires once per listing (checks alert_log).
"""
import os
import resend
from db import supabase_client

ALERT_THRESHOLD = 75
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "sachi@example.com")


def notify_high_scores():
    sb = supabase_client()

    # Get IDs already alerted
    alerted_ids = {
        r["listing_id"]
        for r in sb.table("alert_log").select("listing_id").execute().data
    }

    rows = (
        sb.table("listings")
        .select("*, listing_scores(*)")
        .eq("is_active", True)
        .execute()
        .data
    )

    sent = 0
    for row in rows:
        score_list = row.get("listing_scores") or [{}]
        score = score_list[0].get("total_score", 0)
        if score >= ALERT_THRESHOLD and row["id"] not in alerted_ids:
            try:
                _send_alert(row, score)
                sb.table("alert_log").insert({
                    "listing_id": row["id"],
                    "score": score,
                    "channel": "email",
                }).execute()
                sent += 1
            except Exception as e:
                print(f"[notifier] failed to alert {row['id']}: {e}")

    print(f"[notifier] sent {sent} alert(s)")


def _send_alert(listing: dict, score: int):
    resend.api_key = os.getenv("RESEND_API_KEY")

    score_list = listing.get("listing_scores") or [{}]
    s = score_list[0]
    transit_min = s.get("transit_min", "?")
    school_rating = s.get("school_rating", "?")
    income = s.get("neighbourhood_income", 0)

    tier = "STRONG MATCH" if score >= 80 else "GOOD FIT"

    resend.Emails.send({
        "from": "househunter@yourdomain.com",
        "to": ALERT_EMAIL,
        "subject": f"🏠 {tier}: {listing['address']} — Score {score}/100",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: #002B1A; padding: 24px; border-radius: 8px 8px 0 0;">
            <h1 style="color: #CFBD91; margin: 0; font-size: 20px;">GTA House Hunter</h1>
            <p style="color: #708573; margin: 4px 0 0 0;">New listing matches your criteria</p>
          </div>
          <div style="border: 1px solid #EFEDEE; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
            <div style="background: #F0F7F0; border-left: 4px solid #008A00; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
              <span style="color: #008A00; font-weight: bold; font-size: 13px;">{tier}</span>
              <span style="color: #515B52; font-size: 13px;"> · Score {score}/100</span>
            </div>
            <h2 style="color: #1C1C1C; margin: 0 0 4px 0; font-size: 18px;">{listing['address']}</h2>
            <p style="color: #515B52; margin: 0 0 20px 0;">{listing.get('neighbourhood', 'Toronto')}</p>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
              <tr>
                <td style="padding: 8px; background: #EFEDEE; border-radius: 4px; text-align: center; width: 25%;">
                  <div style="font-size: 20px; font-weight: bold; color: #1C1C1C;">${listing['price']:,}</div>
                  <div style="font-size: 11px; color: #708573;">PRICE</div>
                </td>
                <td style="width: 4px;"></td>
                <td style="padding: 8px; background: #EFEDEE; border-radius: 4px; text-align: center; width: 23%;">
                  <div style="font-size: 20px; font-weight: bold; color: #1C1C1C;">{listing.get('beds', '?')}</div>
                  <div style="font-size: 11px; color: #708573;">BEDS</div>
                </td>
                <td style="width: 4px;"></td>
                <td style="padding: 8px; background: #EFEDEE; border-radius: 4px; text-align: center; width: 23%;">
                  <div style="font-size: 20px; font-weight: bold; color: #1C1C1C;">{listing.get('baths', '?')}</div>
                  <div style="font-size: 11px; color: #708573;">BATHS</div>
                </td>
                <td style="width: 4px;"></td>
                <td style="padding: 8px; background: #EFEDEE; border-radius: 4px; text-align: center; width: 23%;">
                  <div style="font-size: 20px; font-weight: bold; color: #1C1C1C;">{listing.get('sqft', '?')}</div>
                  <div style="font-size: 11px; color: #708573;">SQFT</div>
                </td>
              </tr>
            </table>
            <div style="border-top: 1px solid #EFEDEE; padding-top: 16px; margin-bottom: 20px;">
              <p style="margin: 4px 0; color: #515B52; font-size: 14px;">🏫 School rating: <strong>{school_rating}/10</strong></p>
              <p style="margin: 4px 0; color: #515B52; font-size: 14px;">🚇 Transit to Union: <strong>{transit_min} min</strong></p>
              <p style="margin: 4px 0; color: #515B52; font-size: 14px;">💰 Neighbourhood income: <strong>${income:,}</strong></p>
            </div>
            <a href="{listing.get('realtor_url', 'https://www.realtor.ca')}"
               style="display: inline-block; background: #008A00; color: white; padding: 12px 24px;
                      border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px;">
              View on Realtor.ca →
            </a>
          </div>
        </div>
        """,
    })
