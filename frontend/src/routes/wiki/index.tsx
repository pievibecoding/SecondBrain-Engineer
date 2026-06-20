import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useWikiCategories } from "../../hooks/useWikiCategories";
import { useWikiSearch } from "../../hooks/useWikiSearch";

export function WikiIndexPage() {
  const { categories, loading } = useWikiCategories();
  const { results, search, loading: searching, error } = useWikiSearch();
  const [query, setQuery] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void search(query);
  };

  return (
    <div className="stack">
      <section className="card">
        <h1>Wiki</h1>
        <p>Browse graph entities extracted from Robolinks documents and chat memory.</p>
        <form className="search-form" onSubmit={submit}>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search entity name" />
          <button type="submit" disabled={searching}>Search</button>
        </form>
        {error ? <p className="error">{error.message}</p> : null}
      </section>
      <section className="grid cards-grid">
        {categories.map((category) => (
          <div className="card" key={category.type}>
            <h2>{category.type}</h2>
            <p>{loading ? "Loading..." : `${category.count} entities`}</p>
          </div>
        ))}
      </section>
      {results.length ? (
        <section className="card">
          <h2>Search results</h2>
          <div className="list">
            {results.map((entity) => (
              <Link key={entity.name} to={`/wiki/${encodeURIComponent(entity.name)}`} className="list-row">
                <strong>{entity.name}</strong>
                <span>{entity.type}</span>
                <small>{entity.description}</small>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
