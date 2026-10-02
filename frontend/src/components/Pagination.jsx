export default function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(Math.ceil(total / pageSize), 1);
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between px-4 py-4 border-t border-gray-100">
      <p className="text-sm text-gray-500">
        {total === 0 ? "Showing 0 results" : `Showing ${start} to ${end} of ${total} reports`}
      </p>
      <div className="flex items-center gap-2">
        <button
          className="btn-secondary text-sm px-3 py-1.5"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span className="text-sm text-gray-600 px-2">Page {page}</span>
        <button
          className="btn-secondary text-sm px-3 py-1.5"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
