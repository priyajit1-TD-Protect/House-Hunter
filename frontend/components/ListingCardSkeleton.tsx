export function ListingCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-td-grey overflow-hidden animate-pulse">
      <div className="aspect-[16/9] bg-td-grey" />
      <div className="p-4 space-y-3">
        <div className="h-3 bg-td-grey rounded w-1/3" />
        <div className="h-5 bg-td-grey rounded w-4/5" />
        <div className="h-7 bg-td-grey rounded w-2/5" />
        <div className="flex gap-2">
          <div className="h-6 w-16 bg-td-grey rounded-full" />
          <div className="h-6 w-16 bg-td-grey rounded-full" />
          <div className="h-6 w-20 bg-td-grey rounded-full" />
        </div>
        <div className="h-10 bg-td-grey rounded" />
        <div className="flex justify-between items-center pt-2">
          <div className="h-4 w-24 bg-td-grey rounded" />
          <div className="h-8 w-36 bg-td-grey rounded-lg" />
        </div>
      </div>
    </div>
  );
}
