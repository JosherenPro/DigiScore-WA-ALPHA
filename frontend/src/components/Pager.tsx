type Props = {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
};

export default function Pager({ page, pageSize, total, onPage }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) {
    return total ? <p className="pager-meta">{total} résultat{total > 1 ? "s" : ""}</p> : null;
  }
  return (
    <div className="pager">
      <button className="btn ghost sm" disabled={page <= 1} onClick={() => onPage(page - 1)} type="button">
        Précédent
      </button>
      <span className="pager-meta">
        Page {page} / {pages} · {total.toLocaleString("fr-FR")}
      </span>
      <button className="btn ghost sm" disabled={page >= pages} onClick={() => onPage(page + 1)} type="button">
        Suivant
      </button>
    </div>
  );
}
