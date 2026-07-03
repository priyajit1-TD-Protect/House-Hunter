interface EmptyStateProps {
  onReset?: () => void;
}

export function EmptyState({ onReset }: EmptyStateProps) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-24 text-center">
      <div className="text-5xl mb-4">🏘️</div>
      <h3 className="text-td-nearBlack font-bold text-lg mb-2">
        No listings match your filters
      </h3>
      <p className="text-td-greenGrey text-sm mb-6 max-w-xs">
        Try lowering your minimum score, raising your max price, or choosing a different neighbourhood.
      </p>
      {onReset && (
        <button
          onClick={onReset}
          className="bg-td-digitalGreen text-white text-sm font-bold px-5 py-2.5 rounded-lg
            hover:bg-td-premiumGreen transition-colors"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}
