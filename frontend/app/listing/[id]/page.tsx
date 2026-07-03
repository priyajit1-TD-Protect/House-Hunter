import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Listing } from "@/lib/types";
import {
  formatFullPrice,
  formatIncome,
  formatDate,
  getScore,
  getScoreTier,
} from "@/lib/utils";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { ScoreBar } from "@/components/ScoreBar";

const API = process.env.FASTAPI_URL ?? "http://localhost:8000";

async function getListing(id: string): Promise<Listing | null> {
  try {
    const res = await fetch(`${API}/api/listings/${id}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ListingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const listing = await getListing(params.id);
  if (!listing) notFound();

  const score = getScore(listing);
  const tier = getScoreTier(score);
  const scoreData = listing.listing_scores?.[0];

  return (
    <div className="min-h-screen bg-[#F5F5F5]">
      {/* Back nav */}
      <div className="bg-td-premiumGreen px-4 py-3">
        <div className="max-w-5xl mx-auto">
          <Link
            href="/"
            className="text-td-gold text-sm font-semibold hover:text-white transition-colors"
          >
            ← Back to listings
          </Link>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Left column */}
          <div className="lg:col-span-3 space-y-6">
            {/* Image */}
            <div className="relative aspect-[4/3] bg-td-grey rounded-2xl overflow-hidden">
              {listing.img_url ? (
                <Image
                  src={listing.img_url}
                  alt={listing.address}
                  fill
                  className="object-cover"
                  priority
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-6xl opacity-20">🏠</span>
                </div>
              )}
            </div>

            {/* Address block */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${tier.bg} ${tier.color} ${tier.border}`}>
                  {tier.label}
                </span>
                {listing.listing_type && (
                  <span className="text-xs text-td-greenGrey bg-td-grey px-2.5 py-1 rounded-lg">
                    {listing.listing_type}
                  </span>
                )}
              </div>
              <h1 className="font-display font-black text-td-nearBlack text-2xl mt-2 mb-1">
                {listing.address}
              </h1>
              <p className="text-td-greenGrey">{listing.neighbourhood ?? listing.city}</p>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Price", value: formatFullPrice(listing.price) },
                { label: "Bedrooms", value: listing.beds ? `${listing.beds} bed` : "—" },
                { label: "Bathrooms", value: listing.baths ? `${listing.baths} bath` : "—" },
                { label: "Size", value: listing.sqft ? `${listing.sqft.toLocaleString()} sqft` : "—" },
              ].map((item) => (
                <div key={item.label} className="bg-white rounded-xl border border-td-grey p-4 text-center">
                  <p className="text-xs text-td-greenGrey uppercase tracking-wide mb-1">{item.label}</p>
                  <p className="font-black text-td-nearBlack text-sm">{item.value}</p>
                </div>
              ))}
            </div>

            {/* Neighbourhood signals */}
            {scoreData && (
              <div className="bg-white rounded-xl border border-td-grey p-5">
                <h2 className="font-bold text-td-nearBlack mb-4">Neighbourhood</h2>
                <div className="space-y-3 text-sm text-td-darkGrey">
                  <div className="flex justify-between">
                    <span>🏫 Elementary school (Fraser)</span>
                    <strong>{scoreData.school_rating ?? "—"}/10</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>🚇 Peak transit to Union</span>
                    <strong>{scoreData.transit_min < 99 ? `${scoreData.transit_min} min` : "—"}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>💰 Avg household income</span>
                    <strong>{scoreData.neighbourhood_income ? formatIncome(scoreData.neighbourhood_income) : "—"}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right column — score card */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-2xl border border-td-grey p-6 sticky top-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs text-td-greenGrey uppercase tracking-wide">Match Score</p>
                  <p className="font-black text-td-premiumGreen text-5xl tabular-nums">{score}</p>
                  <p className="text-td-greenGrey text-sm">out of 100</p>
                </div>
                <div className="w-20 h-20 rounded-full border-4 border-td-grey flex items-center justify-center relative">
                  <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="36" fill="none" stroke="#EFEDEE" strokeWidth="6" />
                    <circle
                      cx="40" cy="40" r="36" fill="none"
                      stroke={score >= 80 ? "#008A00" : score >= 65 ? "#708573" : "#FFA500"}
                      strokeWidth="6"
                      strokeDasharray={`${(score / 100) * 226} 226`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="text-td-nearBlack font-black text-lg tabular-nums z-10">{score}</span>
                </div>
              </div>

              <ScoreBar score={score} size="lg" />

              {scoreData && (
                <div className="mt-5 border-t border-td-grey pt-5">
                  <ScoreBreakdown score={scoreData} />
                </div>
              )}

              <div className="mt-6 space-y-3">
                <a
                  href={listing.realtor_url ?? "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full text-center bg-td-digitalGreen text-white font-bold py-3 rounded-xl
                    hover:bg-td-premiumGreen transition-colors"
                >
                  View on Realtor.ca ↗
                </a>
                <p className="text-xs text-center text-td-greenGrey">
                  Listed {formatDate(listing.listed_date)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
